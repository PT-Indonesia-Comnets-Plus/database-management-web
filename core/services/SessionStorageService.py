"""
Session storage service for persistent user sessions across page refreshes.
Works on both local development and Streamlit Cloud deployment.
"""

import streamlit as st
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from streamlit_js_eval import streamlit_js_eval
import uuid
import hashlib

logger = logging.getLogger(__name__)


class SessionStorageService:
    """
    Hybrid session storage service that uses multiple storage mechanisms:
    1. Browser Local Storage (primary)
    2. Database-based session storage (fallback)
    3. Streamlit session state (temporary)
    """

    def __init__(self, db_pool=None, firestore=None):
        """Initialize session storage service."""
        self.db_pool = db_pool
        self.firestore = firestore
        self.session_timeout = timedelta(days=7)  # 7 days session timeout

    def _generate_session_id(self, username: str) -> str:
        """Generate unique session ID for user."""
        timestamp = str(datetime.now().timestamp())
        unique_string = f"{username}_{timestamp}_{uuid.uuid4()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]

    def save_user_session(self, username: str, email: str, role: str) -> bool:
        """
        Save user session using multiple storage mechanisms.
        """
        try:
            session_data = {
                "username": username,
                "email": email,
                "role": role,
                "signout": False,
                "timestamp": datetime.now().isoformat(),
                "session_id": self._generate_session_id(username)
            }

            # 1. Save to Browser Local Storage (Primary method)
            success_local = self._save_to_local_storage(session_data)

            # 2. Save to Database (Fallback method)
            success_db = self._save_to_database(session_data)

            # 3. Update Streamlit session state
            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False
            st.session_state.session_id = session_data["session_id"]

            logger.info(
                f"Session saved for user {username}. Local Storage: {success_local}, Database: {success_db}")
            return success_local or success_db

        except Exception as e:
            logger.error(f"Failed to save user session: {e}")
            return False

    def _save_to_local_storage(self, session_data: Dict[str, Any]) -> bool:
        """Save session data to browser local storage."""
        try:
            # Use streamlit-js-eval to interact with browser localStorage
            js_code = f"""
            try {{
                localStorage.setItem('iconnet_session', JSON.stringify({json.dumps(session_data)}));
                localStorage.setItem('iconnet_session_timestamp', Date.now().toString());
                true;
            }} catch (e) {{
                console.error('Failed to save to localStorage:', e);
                false;
            }}
            """

            result = streamlit_js_eval(js_expressions=js_code)
            return result is True

        except Exception as e:
            logger.error(f"Failed to save to local storage: {e}")
            return False

    def _save_to_database(self, session_data: Dict[str, Any]) -> bool:
        """Save session data to database as fallback."""
        if not self.db_pool:
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Create sessions table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(32) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    session_data JSONB
                )
            """)

            expires_at = datetime.now() + self.session_timeout

            # Insert or update session
            cursor.execute("""
                INSERT INTO user_sessions (session_id, username, email, role, expires_at, session_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) 
                DO UPDATE SET 
                    expires_at = EXCLUDED.expires_at,
                    session_data = EXCLUDED.session_data
            """, (
                session_data["session_id"],
                session_data["username"],
                session_data["email"],
                session_data["role"],
                expires_at,
                json.dumps(session_data)
            ))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            return True

        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
            return False

    def load_user_session(self) -> Optional[Dict[str, Any]]:
        """
        Load user session from available storage mechanisms.
        Priority: Local Storage -> Database -> None
        """
        try:
            # 1. Try to load from Browser Local Storage first
            session_data = self._load_from_local_storage()
            if session_data and self._is_session_valid(session_data):
                self._update_session_state(session_data)
                return session_data

            # 2. Try to load from Database as fallback
            session_data = self._load_from_database()
            if session_data and self._is_session_valid(session_data):
                self._update_session_state(session_data)
                # Re-save to local storage if database session is valid
                self._save_to_local_storage(session_data)
                return session_data

            # 3. No valid session found
            self._clear_session_state()
            return None

        except Exception as e:
            logger.error(f"Failed to load user session: {e}")
            self._clear_session_state()
            return None

    def _load_from_local_storage(self) -> Optional[Dict[str, Any]]:
        """Load session data from browser local storage."""
        try:
            js_code = """
            try {
                const sessionData = localStorage.getItem('iconnet_session');
                const timestamp = localStorage.getItem('iconnet_session_timestamp');
                
                if (sessionData && timestamp) {
                    const data = JSON.parse(sessionData);
                    data.client_timestamp = timestamp;
                    return data;
                }
                return null;
            } catch (e) {
                console.error('Failed to load from localStorage:', e);
                return null;
            }
            """

            result = streamlit_js_eval(js_expressions=js_code)
            return result if isinstance(result, dict) else None

        except Exception as e:
            logger.error(f"Failed to load from local storage: {e}")
            return None

    def _load_from_database(self) -> Optional[Dict[str, Any]]:
        """Load session data from database."""
        if not self.db_pool:
            return None

        try:
            # Try to find session by username from current session state
            username = st.session_state.get("username", "")
            if not username:
                return None

            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Get the latest valid session for this user
            cursor.execute("""
                SELECT session_data, expires_at 
                FROM user_sessions 
                WHERE username = %s AND expires_at > CURRENT_TIMESTAMP 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (username,))

            result = cursor.fetchone()
            cursor.close()
            self.db_pool.putconn(conn)

            if result:
                session_data_str, expires_at = result
                session_data = json.loads(session_data_str)
                return session_data

            return None

        except Exception as e:
            logger.error(f"Failed to load session from database: {e}")
            if 'conn' in locals():
                try:
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
            return None

    def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session data is valid and not expired."""
        try:
            if not session_data:
                return False

            required_fields = ["username", "email", "role", "timestamp"]
            if not all(field in session_data for field in required_fields):
                return False

            # Check if session is not marked as signed out
            if session_data.get("signout", True):
                return False

            # Check session timestamp (not older than timeout period)
            session_time = datetime.fromisoformat(session_data["timestamp"])
            if datetime.now() - session_time > self.session_timeout:
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to validate session: {e}")
            return False

    def _update_session_state(self, session_data: Dict[str, Any]) -> None:
        """Update Streamlit session state with loaded session data."""
        st.session_state.username = session_data.get("username", "")
        st.session_state.useremail = session_data.get("email", "")
        st.session_state.role = session_data.get("role", "")
        st.session_state.signout = session_data.get("signout", True)
        st.session_state.session_id = session_data.get("session_id", "")

    def _clear_session_state(self) -> None:
        """Clear session state variables."""
        st.session_state.username = ""
        st.session_state.useremail = ""
        st.session_state.role = ""
        st.session_state.signout = True
        if "session_id" in st.session_state:
            del st.session_state.session_id

    def clear_user_session(self, username: str = None) -> bool:
        """
        Clear user session from all storage mechanisms.
        """
        try:
            success_count = 0

            # 1. Clear from Local Storage
            if self._clear_from_local_storage():
                success_count += 1

            # 2. Clear from Database
            if self._clear_from_database(username):
                success_count += 1

            # 3. Clear from Session State
            self._clear_session_state()
            success_count += 1

            logger.info(
                f"Session cleared for user {username}. Cleared from {success_count}/3 storage mechanisms.")
            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to clear user session: {e}")
            return False

    def _clear_from_local_storage(self) -> bool:
        """Clear session data from browser local storage."""
        try:
            js_code = """
            try {
                localStorage.removeItem('iconnet_session');
                localStorage.removeItem('iconnet_session_timestamp');
                true;
            } catch (e) {
                console.error('Failed to clear localStorage:', e);
                false;
            }
            """

            result = streamlit_js_eval(js_expressions=js_code)
            return result is True

        except Exception as e:
            logger.error(f"Failed to clear local storage: {e}")
            return False

    def _clear_from_database(self, username: str = None) -> bool:
        """Clear session data from database."""
        if not self.db_pool:
            return False

        try:
            username = username or st.session_state.get("username", "")
            if not username:
                return False

            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Delete all sessions for this user
            cursor.execute(
                "DELETE FROM user_sessions WHERE username = %s", (username,))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            return True

        except Exception as e:
            logger.error(f"Failed to clear session from database: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
            return False

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions from database."""
        if not self.db_pool:
            return

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Delete expired sessions
            cursor.execute(
                "DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP")

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass

    def is_user_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        try:
            # First check session state
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)

            if username and not signout:
                return True

            # If session state is empty, try to load from storage
            session_data = self.load_user_session()
            return session_data is not None

        except Exception as e:
            logger.error(f"Failed to check authentication status: {e}")
            return False


# Global session storage service instance
_session_storage_service: Optional[SessionStorageService] = None


def get_session_storage_service(db_pool=None, firestore=None) -> SessionStorageService:
    """Get or create the global session storage service instance."""
    global _session_storage_service
    if _session_storage_service is None:
        _session_storage_service = SessionStorageService(db_pool, firestore)
    return _session_storage_service

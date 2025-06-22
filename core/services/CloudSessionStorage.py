"""
Advanced session storage service for Streamlit Cloud deployment.
Handles session persistence using multiple storage mechanisms with cloud-optimized fallbacks.
"""

import streamlit as st
import json
import logging
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import base64

# Try different storage mechanisms
HAS_JS_EVAL = False
HAS_EXTRA_STREAMLIT = False
HAS_COOKIES_MANAGER = False

try:
    from streamlit_js_eval import streamlit_js_eval
    HAS_JS_EVAL = True
    logger = logging.getLogger(__name__)
    logger.info("streamlit-js-eval available")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("streamlit-js-eval not available")

try:
    import extra_streamlit_components as stx
    HAS_EXTRA_STREAMLIT = True
    logger.info("extra-streamlit-components available")
except ImportError:
    logger.warning("extra-streamlit-components not available")

try:
    from streamlit_cookies_manager import EncryptedCookieManager
    HAS_COOKIES_MANAGER = True
    logger.info("streamlit-cookies-manager available")
except ImportError:
    logger.warning("streamlit-cookies-manager not available")


class CloudSessionStorage:
    """
    Cloud-optimized session storage for Streamlit Cloud deployment.
    Uses multiple fallback mechanisms to ensure session persistence.
    """

    def __init__(self, db_pool=None, app_prefix="iconnet_app"):
        self.db_pool = db_pool
        self.app_prefix = app_prefix
        self.session_timeout = timedelta(days=7)

        # Initialize available storage mechanisms
        self._init_storage_mechanisms()

    def _init_storage_mechanisms(self):
        """Initialize available storage mechanisms based on what's available."""
        self.storage_methods = []

        # Method 1: Database storage (most reliable for cloud deployment)
        if self.db_pool:
            self.storage_methods.append("database")
            logger.info("Database storage available - prioritized for cloud")

        # Method 2: extra-streamlit-components cookie manager
        if HAS_EXTRA_STREAMLIT:
            try:
                self.stx_cookie_manager = stx.CookieManager()
                # Test if STX cookies are working
                test_key = f"{self.app_prefix}_test"
                test_value = "test_value"
                self.stx_cookie_manager.set(test_key, test_value)
                if self.stx_cookie_manager.get(test_key) == test_value:
                    self.storage_methods.append("stx_cookies")
                    logger.info(
                        "STX Cookie Manager initialized and tested successfully")
                    # Clean up test cookie
                    self.stx_cookie_manager.delete(test_key)
                else:
                    logger.warning(
                        "STX Cookie Manager test failed - cookies not working")
            except Exception as e:
                logger.error(f"Failed to initialize STX Cookie Manager: {e}")

        # Method 3: Browser localStorage via JS eval
        if HAS_JS_EVAL:
            self.storage_methods.append("js_local_storage")
            logger.info("JS LocalStorage available")

        # Method 4: legacy cookies manager (fallback)
        if HAS_COOKIES_MANAGER:
            try:
                cookie_password = st.secrets.get(
                    "cookie_password", "iconnet_secure_key_2024")
                self.legacy_cookies = EncryptedCookieManager(
                    prefix=f"{self.app_prefix}_legacy",
                    password=cookie_password
                )
                if self.legacy_cookies.ready():
                    self.storage_methods.append("legacy_cookies")
                    logger.info("Legacy cookies initialized")
            except Exception as e:
                # Method 5: Session state (always available, temporary)
                logger.error(f"Failed to initialize legacy cookies: {e}")
        self.storage_methods.append("session_state")

        logger.info(f"Available storage methods: {self.storage_methods}")

    def save_session(self, username: str, email: str, role: str,
                     login_timestamp: Optional[str] = None, session_expiry: Optional[str] = None) -> bool:
        """Save user session using all available storage mechanisms."""
        # Use provided timestamps or generate new ones
        current_time = datetime.now()
        login_time = datetime.fromisoformat(
            login_timestamp) if login_timestamp else current_time
        expiry_time = datetime.fromisoformat(session_expiry) if session_expiry else (
            current_time + self.session_timeout)

        session_data = {
            "username": username,
            "email": email,
            "role": role,
            "signout": False,
            "timestamp": current_time.isoformat(),
            "login_timestamp": login_time.isoformat(),
            "session_expiry": expiry_time.isoformat(),
            "session_id": self._generate_session_id(username),
            "expires_at": expiry_time.isoformat()
        }

        success_count = 0

        # Try each storage method
        for method in self.storage_methods:
            try:
                if method == "stx_cookies" and hasattr(self, 'stx_cookie_manager'):
                    if self._save_stx_cookies(session_data):
                        success_count += 1
                        logger.info("Session saved to STX cookies")

                elif method == "legacy_cookies" and hasattr(self, 'legacy_cookies'):
                    if self._save_legacy_cookies(session_data):
                        success_count += 1
                        logger.info("Session saved to legacy cookies")

                elif method == "js_local_storage":
                    if self._save_js_localStorage(session_data):
                        success_count += 1
                        logger.info("Session saved to JS localStorage")

                elif method == "database":
                    if self._save_database(session_data):
                        success_count += 1
                        logger.info("Session saved to database")

                elif method == "session_state":
                    self._save_session_state(session_data)
                    success_count += 1
                    logger.info("Session saved to session state")

            except Exception as e:
                logger.error(f"Failed to save session using {method}: {e}")

        logger.info(
            f"Session saved using {success_count}/{len(self.storage_methods)} methods")
        return success_count > 0

    def load_session(self) -> Optional[Dict[str, Any]]:
        """Load user session from available storage mechanisms."""
        # Try loading from each method in priority order
        for method in self.storage_methods:
            try:
                session_data = None

                if method == "stx_cookies" and hasattr(self, 'stx_cookie_manager'):
                    session_data = self._load_stx_cookies()

                elif method == "legacy_cookies" and hasattr(self, 'legacy_cookies'):
                    session_data = self._load_legacy_cookies()

                elif method == "js_local_storage":
                    session_data = self._load_js_localStorage()

                elif method == "database":
                    session_data = self._load_database()

                elif method == "session_state":
                    session_data = self._load_session_state()

                if session_data and self._is_session_valid(session_data):
                    logger.info(f"Valid session loaded from {method}")
                    self._update_session_state(session_data)

                    # Re-save to other methods if this was from database/fallback
                    if method in ["database", "session_state"]:
                        self._resave_to_persistent_storage(session_data)

                    return session_data

            except Exception as e:
                logger.error(f"Failed to load session from {method}: {e}")

        logger.info("No valid session found in any storage method")
        self._clear_session_state()
        return None

    def clear_session(self, username: str = None) -> bool:
        """Clear session from all storage mechanisms."""
        success_count = 0
        username = username or st.session_state.get("username", "")

        for method in self.storage_methods:
            try:
                if method == "stx_cookies" and hasattr(self, 'stx_cookie_manager'):
                    if self._clear_stx_cookies():
                        success_count += 1

                elif method == "legacy_cookies" and hasattr(self, 'legacy_cookies'):
                    if self._clear_legacy_cookies():
                        success_count += 1

                elif method == "js_local_storage":
                    if self._clear_js_localStorage():
                        success_count += 1

                elif method == "database":
                    if self._clear_database(username):
                        success_count += 1

                elif method == "session_state":
                    self._clear_session_state()
                    success_count += 1

            except Exception as e:
                logger.error(f"Failed to clear session from {method}: {e}")

        logger.info(
            f"Session cleared from {success_count}/{len(self.storage_methods)} methods")
        return success_count > 0

    # STX Cookies Implementation (Most reliable for Streamlit Cloud)
    def _save_stx_cookies(self, session_data: Dict[str, Any]) -> bool:
        """Save session using extra-streamlit-components cookie manager."""
        try:
            encoded_data = base64.b64encode(
                json.dumps(session_data).encode()).decode()

            # Use STX cookie manager with expiry
            expires_at = datetime.now() + self.session_timeout

            self.stx_cookie_manager.set(
                cookie=f"{self.app_prefix}_session",
                val=encoded_data,
                expires_at=expires_at
            )
            return True
        except Exception as e:
            logger.error(f"STX cookie save failed: {e}")
            return False

    def _load_stx_cookies(self) -> Optional[Dict[str, Any]]:
        """Load session from STX cookies."""
        try:
            encoded_data = self.stx_cookie_manager.get(
                f"{self.app_prefix}_session")
            if encoded_data:
                session_data = json.loads(
                    base64.b64decode(encoded_data).decode())
                return session_data
        except Exception as e:
            logger.error(f"STX cookie load failed: {e}")
        return None

    def _clear_stx_cookies(self) -> bool:
        """Clear STX cookies."""
        try:
            self.stx_cookie_manager.delete(f"{self.app_prefix}_session")
            return True
        except Exception as e:
            logger.error(f"STX cookie clear failed: {e}")
            return False

    # Legacy Cookies Implementation
    def _save_legacy_cookies(self, session_data: Dict[str, Any]) -> bool:
        """Save session using legacy cookies manager."""
        try:
            if not self.legacy_cookies.ready():
                return False

            for key, value in session_data.items():
                self.legacy_cookies[key] = str(value)
            self.legacy_cookies.save()
            return True
        except Exception as e:
            logger.error(f"Legacy cookie save failed: {e}")
            return False

    def _load_legacy_cookies(self) -> Optional[Dict[str, Any]]:
        """Load session from legacy cookies."""
        try:
            if not self.legacy_cookies.ready():
                return None

            session_data = {}
            for key in ["username", "email", "role", "signout", "timestamp", "session_id", "expires_at"]:
                value = self.legacy_cookies.get(key)
                if value:
                    session_data[key] = value

            if session_data.get("username"):
                # Convert signout to boolean
                session_data["signout"] = session_data.get(
                    "signout", "True") == "True"
                return session_data
        except Exception as e:
            logger.error(f"Legacy cookie load failed: {e}")
        return None

    def _clear_legacy_cookies(self) -> bool:
        """Clear legacy cookies."""
        try:
            if not self.legacy_cookies.ready():
                return False

            for key in ["username", "email", "role", "signout", "timestamp", "session_id", "expires_at"]:
                self.legacy_cookies[key] = ""
            self.legacy_cookies.save()
            return True
        except Exception as e:
            logger.error(f"Legacy cookie clear failed: {e}")
            return False

    # JavaScript localStorage Implementation
    def _save_js_localStorage(self, session_data: Dict[str, Any]) -> bool:
        """Save session using JavaScript localStorage."""
        try:
            js_code = f"""
            try {{
                const sessionData = {json.dumps(session_data)};
                localStorage.setItem('{self.app_prefix}_session', JSON.stringify(sessionData));
                localStorage.setItem('{self.app_prefix}_timestamp', Date.now().toString());
                true;
            }} catch (e) {{
                console.error('LocalStorage save failed:', e);
                false;
            }}
            """
            result = streamlit_js_eval(js_expressions=js_code)
            return result is True
        except Exception as e:
            logger.error(f"JS localStorage save failed: {e}")
            return False

    def _load_js_localStorage(self) -> Optional[Dict[str, Any]]:
        """Load session from JavaScript localStorage."""
        try:
            js_code = f"""
            try {{
                const sessionData = localStorage.getItem('{self.app_prefix}_session');
                if (sessionData) {{
                    return JSON.parse(sessionData);
                }}
                return null;
            }} catch (e) {{
                console.error('LocalStorage load failed:', e);
                return null;
            }}
            """
            result = streamlit_js_eval(js_expressions=js_code)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"JS localStorage load failed: {e}")
            return None

    def _clear_js_localStorage(self) -> bool:
        """Clear JavaScript localStorage."""
        try:
            js_code = f"""
            try {{
                localStorage.removeItem('{self.app_prefix}_session');
                localStorage.removeItem('{self.app_prefix}_timestamp');
                true;
            }} catch (e) {{
                console.error('LocalStorage clear failed:', e);
                false;
            }}
            """
            result = streamlit_js_eval(js_expressions=js_code)
            return result is True
        except Exception as e:
            logger.error(f"JS localStorage clear failed: {e}")
            return False

    # Database Implementation
    def _save_database(self, session_data: Dict[str, Any]) -> bool:
        """Save session to database."""
        if not self.db_pool:
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_user_sessions (
                    session_id VARCHAR(32) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    session_data JSONB,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            expires_at = datetime.fromisoformat(session_data["expires_at"])

            cursor.execute("""
                INSERT INTO cloud_user_sessions 
                (session_id, username, email, role, expires_at, session_data, last_accessed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) 
                DO UPDATE SET 
                    expires_at = EXCLUDED.expires_at,
                    session_data = EXCLUDED.session_data,
                    last_accessed = CURRENT_TIMESTAMP
            """, (
                session_data["session_id"],                session_data["username"],
                session_data["email"],
                session_data["role"],
                expires_at,
                json.dumps(session_data),
                datetime.now()
            ))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)
            return True

        except Exception as e:
            logger.error(f"Database save failed: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
            return False

    def _load_database(self) -> Optional[Dict[str, Any]]:
        """Load session from database."""
        if not self.db_pool:
            return None

        try:
            # Try to get session by username first
            username = st.session_state.get("username", "")
            session_id = st.session_state.get("session_id", "")

            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # First try by session_id if available
            if session_id:
                cursor.execute("""
                    SELECT session_data, expires_at 
                    FROM cloud_user_sessions 
                    WHERE session_id = %s AND expires_at > CURRENT_TIMESTAMP 
                    ORDER BY last_accessed DESC 
                    LIMIT 1
                """, (session_id,))
                result = cursor.fetchone()
                if result:
                    session_data_str, expires_at = result
                    cursor.close()
                    self.db_pool.putconn(conn)
                    try:
                        # Handle both string and dict from database
                        if isinstance(session_data_str, str):
                            return json.loads(session_data_str)
                        elif isinstance(session_data_str, dict):
                            return session_data_str
                        else:
                            logger.warning(
                                f"Unexpected session_data type from DB: {type(session_data_str)}")
                            return None
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(
                            f"Failed to parse session data from database: {e}")
                        return None

            # Fallback: try by username if session_id didn't work
            if username:
                cursor.execute("""
                    SELECT session_data, expires_at 
                    FROM cloud_user_sessions 
                    WHERE username = %s AND expires_at > CURRENT_TIMESTAMP 
                    ORDER BY last_accessed DESC 
                    LIMIT 1
                """, (username,))
                result = cursor.fetchone()

                if result:
                    session_data_str, expires_at = result
                    cursor.close()
                    self.db_pool.putconn(conn)
                    try:
                        # Handle both string and dict from database
                        if isinstance(session_data_str, str):
                            return json.loads(session_data_str)
                        elif isinstance(session_data_str, dict):
                            return session_data_str
                        else:
                            logger.warning(
                                f"Unexpected session_data type from DB: {type(session_data_str)}")
                            return None
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(
                            f"Failed to parse session data from database: {e}")
                        return None

            cursor.close()
            self.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"Database load failed: {e}")
            if 'conn' in locals():
                try:
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
        return None

    def _clear_database(self, username: str) -> bool:
        """Clear session from database."""
        if not self.db_pool or not username:
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM cloud_user_sessions WHERE username = %s", (username,))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)
            return True

        except Exception as e:
            logger.error(f"Database clear failed: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
            return False

    # Session State Implementation
    def _save_session_state(self, session_data: Dict[str, Any]) -> None:
        """Save session to Streamlit session state."""
        st.session_state.username = session_data.get("username", "")
        st.session_state.useremail = session_data.get("email", "")
        st.session_state.role = session_data.get("role", "")
        st.session_state.signout = session_data.get("signout", True)
        st.session_state.session_id = session_data.get("session_id", "")

    def _load_session_state(self) -> Optional[Dict[str, Any]]:
        """Load session from Streamlit session state."""
        username = st.session_state.get("username", "")
        if username and not st.session_state.get("signout", True):
            return {
                "username": username,
                "email": st.session_state.get("useremail", ""),
                "role": st.session_state.get("role", ""),
                "signout": st.session_state.get("signout", True),
                "session_id": st.session_state.get("session_id", ""),
                "timestamp": datetime.now().isoformat(),
                "expires_at": (datetime.now() + self.session_timeout).isoformat()
            }
        return None

    def _clear_session_state(self) -> None:
        """Clear Streamlit session state."""
        try:
            st.session_state.username = ""
            st.session_state.useremail = ""
            st.session_state.role = ""
            st.session_state.signout = True
            if "session_id" in st.session_state:
                del st.session_state.session_id
        except Exception as e:
            logger.error(f"Failed to clear session state: {e}")

    def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session data is valid and not expired."""
        try:
            if not session_data or not isinstance(session_data, dict):
                return False

            if not session_data.get("username"):
                return False

            if session_data.get("signout", True):
                return False            # Check expiration - try both session_expiry and expires_at
            expiry_str = session_data.get(
                "session_expiry") or session_data.get("expires_at")
            if expiry_str:
                try:
                    expiry_time = datetime.fromisoformat(expiry_str)
                    if datetime.now() > expiry_time:
                        logger.info("Session expired")
                        return False
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid expiry format: {expiry_str}, error: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False

    def _update_session_state(self, session_data: Dict[str, Any]) -> None:
        """Update Streamlit session state with loaded session data."""
        try:
            st.session_state.username = session_data.get("username", "")
            st.session_state.useremail = session_data.get("email", "")
            st.session_state.role = session_data.get("role", "")
            st.session_state.signout = session_data.get("signout", True)
            st.session_state.session_id = session_data.get("session_id", "")

            # Set session timing for timeout logic
            st.session_state.login_timestamp = session_data.get(
                "login_timestamp", "")
            st.session_state.session_expiry = session_data.get(
                "session_expiry", "")

            logger.info("Session state updated with loaded session data")
        except Exception as e:
            logger.error(f"Failed to update session state: {e}")

    # Utility methods
    def _generate_session_id(self, username: str) -> str:
        """Generate unique session ID."""
        timestamp = str(datetime.now().timestamp())
        unique_string = f"{username}_{timestamp}_{uuid.uuid4()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]

    def _generate_browser_fingerprint(self) -> str:
        """Generate a browser fingerprint for session identification when username is not available."""
        try:
            # Use a combination of available session data for consistency
            # This will be consistent across page refreshes for the same browser session
            if "browser_fingerprint" not in st.session_state:
                # Generate a new fingerprint and store it in session state
                # This will persist during the browser session but reset on new session
                fingerprint_data = f"iconnet_browser_{uuid.uuid4()}"
                st.session_state.browser_fingerprint = hashlib.md5(
                    fingerprint_data.encode()).hexdigest()[:16]

            return st.session_state.browser_fingerprint

        except Exception as e:
            logger.warning(f"Could not generate browser fingerprint: {e}")
            # Ultimate fallback - use a simple UUID
            return str(uuid.uuid4())[:16]

    def load_session_by_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Try to load session using browser fingerprint when username is not available."""
        try:
            fingerprint = self._generate_browser_fingerprint()

            # Check if we have this fingerprint stored in session state
            stored_fingerprint = st.session_state.get("browser_fingerprint")
            if stored_fingerprint != fingerprint:
                # Store new fingerprint
                st.session_state.browser_fingerprint = fingerprint

            # Try to load from database using fingerprint as backup identifier
            if self.db_pool:
                try:
                    conn = self.db_pool.getconn()
                    cursor = conn.cursor()

                    # Look for recent sessions that might belong to this browser
                    cursor.execute("""
                        SELECT session_data, expires_at, username
                        FROM cloud_user_sessions 
                        WHERE expires_at > CURRENT_TIMESTAMP 
                        AND last_accessed > NOW() - INTERVAL '1 hour'
                        ORDER BY last_accessed DESC 
                        LIMIT 5
                    """)

                    results = cursor.fetchall()
                    cursor.close()
                    # Try to match with stored sessions
                    self.db_pool.putconn(conn)
                    for session_data_str, expires_at, username in results:
                        try:
                            # Handle both string and dict session_data from database
                            if isinstance(session_data_str, str):
                                session_data = json.loads(session_data_str)
                            elif isinstance(session_data_str, dict):
                                session_data = session_data_str
                            else:
                                logger.warning(
                                    f"Unexpected session_data type: {type(session_data_str)}")
                                continue

                            if self._is_session_valid(session_data):
                                logger.info(
                                    f"Potential session found for browser fingerprint: {username}")
                                return session_data
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(
                                f"Failed to parse session data for user {username}: {e}")
                            continue

                except Exception as e:
                    logger.error(f"Database fingerprint lookup failed: {e}")
                    if 'conn' in locals():
                        try:
                            cursor.close()
                            self.db_pool.putconn(conn)
                        except:
                            pass

            return None

        except Exception as e:
            logger.error(f"Browser fingerprint session loading failed: {e}")
            return None

    def is_user_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        try:
            # Quick check from session state
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)

            if username and not signout:
                return True

            # Try loading from storage
            session_data = self.load_session()
            return session_data is not None

        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions from database."""
        if not self.db_pool:
            return

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM cloud_user_sessions WHERE expires_at < CURRENT_TIMESTAMP")

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} expired cloud sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired cloud sessions: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass

    def _resave_to_persistent_storage(self, session_data: Dict[str, Any]) -> None:
        """Re-save session data to persistent storage methods for backup."""
        try:
            # Try to save to STX cookies if available
            if "stx_cookies" in self.storage_methods and hasattr(self, 'stx_cookie_manager'):
                try:
                    self._save_stx_cookies(session_data)
                    logger.info("Session re-saved to STX cookies")
                except Exception as e:
                    logger.warning(f"Failed to re-save to STX cookies: {e}")

            # Try to save to database if available
            if "database" in self.storage_methods and self.db_pool:
                try:
                    self._save_database(session_data)
                    logger.info("Session re-saved to database")
                except Exception as e:
                    logger.warning(f"Failed to re-save to database: {e}")

        except Exception as e:
            logger.error(
                f"Failed to re-save session to persistent storage: {e}")


# Global instance
_cloud_session_storage: Optional[CloudSessionStorage] = None


def get_cloud_session_storage(db_pool=None, app_prefix="iconnet_app") -> CloudSessionStorage:
    """Get or create the global cloud session storage instance."""
    global _cloud_session_storage
    if _cloud_session_storage is None:
        _cloud_session_storage = CloudSessionStorage(db_pool, app_prefix)
    return _cloud_session_storage

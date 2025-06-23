"""
Persistent Session Service for Streamlit Cloud
Uses Firestore to store session data that persists across page refreshes.
"""

import streamlit as st
import logging
import hashlib
import json
import time
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PersistentSessionService:
    """Handles persistent session storage using Firestore."""

    def __init__(self):
        self.collection_name = "user_sessions"
        self.session_timeout_hours = 24  # Sessions expire after 24 hours

    def _get_firestore(self):
        """Get Firestore client from session state."""
        if "fs" not in st.session_state or st.session_state.fs is None:
            logger.error("Firestore not available")
            return None
        return st.session_state.fs

    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    def _get_session_id(self, username: str) -> str:
        """Generate a consistent session ID for a user."""
        # Use a combination of username and a secret to create session ID
        secret_key = "iconnet_session_2024"  # In production, use st.secrets
        combined = f"{username}_{secret_key}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def save_session(self, username: str, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Save user session to Firestore.

        Args:
            username: The username
            user_data: Dictionary containing user data to persist

        Returns:
            Session token if successful, None otherwise
        """
        try:
            fs = self._get_firestore()
            if fs is None:
                return None

            session_token = self._generate_session_token()
            session_id = self._get_session_id(username)

            # Prepare session data
            session_data = {
                'username': username,
                'session_token': session_token,
                'user_data': user_data,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=self.session_timeout_hours),
                'last_accessed': datetime.utcnow()
            }

            # Save to Firestore
            doc_ref = fs.collection(self.collection_name).document(session_id)
            doc_ref.set(session_data)

            # Store session token in session state and browser cookie
            st.session_state.session_token = session_token
            st.session_state.session_id = session_id

            # Try to set browser cookie using query params or session state
            self._set_browser_session_token(session_token)

            logger.info(f"✅ Session saved to Firestore for user: {username}")
            return session_token

        except Exception as e:
            logger.error(f"Failed to save session to Firestore: {e}")
            return None

    def restore_session(self, session_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Restore user session from Firestore.

        Args:
            session_token: Optional session token. If not provided, will try to get from browser

        Returns:
            User data if session is valid, None otherwise
        """
        try:
            fs = self._get_firestore()
            if fs is None:
                return None

            # Get session token from various sources
            if session_token is None:
                session_token = self._get_browser_session_token()

            if session_token is None:
                logger.info("No session token found")
                return None

            # Search for session in Firestore
            sessions_ref = fs.collection(self.collection_name)
            query = sessions_ref.where(
                'session_token', '==', session_token).limit(1)
            docs = query.stream()

            for doc in docs:
                session_data = doc.to_dict()

                # Check if session is expired
                if session_data['expires_at'] < datetime.utcnow():
                    logger.info("Session expired, deleting")
                    doc.reference.delete()
                    return None

                # Update last accessed time
                doc.reference.update({'last_accessed': datetime.utcnow()})

                # Restore session state
                username = session_data['username']
                user_data = session_data['user_data']

                # Set session state
                st.session_state.username = username
                st.session_state.logged_in = True
                st.session_state.session_token = session_token
                st.session_state.session_id = doc.id

                # Restore user data
                for key, value in user_data.items():
                    st.session_state[key] = value

                logger.info(
                    f"✅ Session restored from Firestore for user: {username}")
                return user_data

            logger.info("No valid session found in Firestore")
            return None

        except Exception as e:
            logger.error(f"Failed to restore session from Firestore: {e}")
            return None

    def clear_session(self, username: Optional[str] = None):
        """Clear user session from Firestore."""
        try:
            fs = self._get_firestore()
            if fs is None:
                return

            # Get session ID
            if username:
                session_id = self._get_session_id(username)
            elif "session_id" in st.session_state:
                session_id = st.session_state.session_id
            else:
                logger.warning("No session ID found to clear")
                return

            # Delete from Firestore
            doc_ref = fs.collection(self.collection_name).document(session_id)
            doc_ref.delete()

            # Clear session state
            session_keys = [
                'username', 'logged_in', 'session_token', 'session_id',
                'user_role', 'user_email', 'user_data'
            ]
            for key in session_keys:
                if key in st.session_state:
                    del st.session_state[key]

            # Clear browser token
            self._clear_browser_session_token()

            logger.info(f"Session cleared for user: {username}")

        except Exception as e:
            logger.error(f"Failed to clear session: {e}")

    def cleanup_expired_sessions(self):
        """Clean up expired sessions from Firestore."""
        try:
            fs = self._get_firestore()
            if fs is None:
                return

            # Query for expired sessions
            sessions_ref = fs.collection(self.collection_name)
            query = sessions_ref.where('expires_at', '<', datetime.utcnow())

            expired_sessions = query.stream()
            deleted_count = 0

            for doc in expired_sessions:
                doc.reference.delete()
                deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")

    def _set_browser_session_token(self, token: str):
        """Store session token in browser using available methods."""
        try:
            # Use query parameters for Streamlit Cloud
            if "query_params" not in st.session_state:
                st.session_state.query_params = {}
            st.session_state.query_params["session_token"] = token

            # Also store in session state as backup
            st.session_state.persistent_session_token = token

        except Exception as e:
            logger.error(f"Failed to set browser session token: {e}")

    def _get_browser_session_token(self) -> Optional[str]:
        """Get session token from browser storage."""
        try:
            # Try session state backup first
            if "persistent_session_token" in st.session_state:
                return st.session_state.persistent_session_token

            # Try to get from URL query params (if available)
            try:
                if hasattr(st, 'query_params'):
                    query_params = st.query_params
                    if "session_token" in query_params:
                        return query_params["session_token"]
            except Exception:
                pass

            return None

        except Exception as e:
            logger.error(f"Failed to get browser session token: {e}")
            return None

    def _clear_browser_session_token(self):
        """Clear session token from browser storage."""
        try:
            # Clear from session state
            if "persistent_session_token" in st.session_state:
                del st.session_state.persistent_session_token

            # Clear query params
            if "query_params" in st.session_state:
                st.session_state.query_params.pop("session_token", None)

        except Exception as e:
            logger.error(f"Failed to clear browser session token: {e}")


# Global instance
_persistent_session_service = None


def get_persistent_session_service() -> PersistentSessionService:
    """Get the global persistent session service instance."""
    global _persistent_session_service
    if _persistent_session_service is None:
        _persistent_session_service = PersistentSessionService()
    return _persistent_session_service

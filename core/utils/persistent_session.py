"""
Persistent session management untuk Streamlit yang bekerja di semua environment.
Menggunakan kombinasi URL query parameters dan localStorage untuk maksimal reliability.
"""

import streamlit as st
import json
import base64
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode, parse_qs
import time

logger = logging.getLogger(__name__)


class PersistentSessionManager:
    """
    Manager untuk session persistence yang robust dan bekerja di semua environment.
    Menggunakan kombinasi URL query parameters dan browser localStorage.
    """

    def __init__(self):
        self.session_key = "iconnet_session"
        self.max_age_seconds = 7 * 24 * 60 * 60  # 7 days

    def save_session(self, username: str, email: str, role: str) -> bool:
        """
        Simpan session dengan multiple persistence methods.

        Args:
            username: Username user
            email: Email user  
            role: Role user

        Returns:
            bool: True jika berhasil disimpan
        """
        session_data = {
            "username": username,
            "email": email,
            "role": role,
            "timestamp": time.time(),
            "signout": False
        }

        success = False

        # Method 1: Save to Streamlit session state (baseline)
        try:
            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False
            st.session_state.last_login_time = time.time()
            st.session_state._persistent_session_data = session_data
            success = True
            logger.info(f"Session saved to session state: {username}")
        except Exception as e:
            logger.error(f"Failed to save to session state: {e}")

        # Method 2: Save to URL query parameters (most reliable for refresh)
        try:
            self._update_url_with_session(session_data)
            logger.info(f"Session saved to URL: {username}")
        except Exception as e:
            logger.warning(f"Failed to save to URL: {e}")

        # Method 3: Try localStorage via JavaScript (if browser available)
        try:
            self._save_to_localstorage(session_data)
            logger.info(f"Session saved to localStorage: {username}")
        except Exception as e:
            logger.warning(f"Failed to save to localStorage: {e}")

        return success

    def load_session(self) -> bool:
        """
        Load session dari berbagai sumber dengan prioritas terurut.

        Returns:
            bool: True jika session berhasil di-restore
        """
        # Priority 1: URL query parameters (paling reliable untuk refresh)
        if self._load_from_url():
            logger.info("Session restored from URL")
            return True

        # Priority 2: Session state persistent data
        if self._load_from_session_state():
            logger.info("Session restored from session state")
            return True

        # Priority 3: localStorage
        if self._load_from_localstorage():
            logger.info("Session restored from localStorage")
            return True

        logger.debug("No persistent session found")
        return False

    def clear_session(self) -> None:
        """Clear session dari semua sumber."""
        # Clear session state
        try:
            st.session_state.username = ""
            st.session_state.useremail = ""
            st.session_state.role = ""
            st.session_state.signout = True
            if hasattr(st.session_state, '_persistent_session_data'):
                delattr(st.session_state, '_persistent_session_data')
            logger.info("Session state cleared")
        except Exception as e:
            logger.error(f"Error clearing session state: {e}")

        # Clear URL parameters
        try:
            self._clear_url_session()
            logger.info("URL session cleared")
        except Exception as e:
            logger.warning(f"Error clearing URL session: {e}")

        # Clear localStorage
        try:
            self._clear_localstorage()
            logger.info("localStorage cleared")
        except Exception as e:
            logger.warning(f"Error clearing localStorage: {e}")

    def is_authenticated(self) -> bool:
        """Check apakah user authenticated."""
        try:
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)
            return bool(username.strip()) and not signout
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False

    def _update_url_with_session(self, session_data: Dict[str, Any]) -> None:
        """Update URL dengan session data sebagai query parameters."""
        try:
            # Encode session data
            encoded_data = base64.urlsafe_b64encode(
                json.dumps(session_data).encode()
            ).decode()

            # Use st.query_params to update URL
            st.query_params[self.session_key] = encoded_data

        except Exception as e:
            logger.error(f"Failed to update URL with session: {e}")
            raise

    def _load_from_url(self) -> bool:
        """Load session dari URL query parameters."""
        try:
            session_param = st.query_params.get(self.session_key)
            if not session_param:
                return False

            # Decode session data
            session_data = json.loads(
                base64.urlsafe_b64decode(session_param.encode()).decode()
            )

            # Validate session age
            if time.time() - session_data.get("timestamp", 0) > self.max_age_seconds:
                logger.info("URL session expired")
                self._clear_url_session()
                return False

            # Restore session
            if self._restore_session_data(session_data):
                return True

        except Exception as e:
            logger.error(f"Error loading from URL: {e}")

        return False

    def _load_from_session_state(self) -> bool:
        """Load session dari session state persistent data."""
        try:
            session_data = st.session_state.get('_persistent_session_data')
            if not session_data:
                return False

            # Validate session age
            if time.time() - session_data.get("timestamp", 0) > self.max_age_seconds:
                logger.info("Session state data expired")
                return False

            return self._restore_session_data(session_data)

        except Exception as e:
            logger.error(f"Error loading from session state: {e}")

        return False

    def _save_to_localstorage(self, session_data: Dict[str, Any]) -> None:
        """Save session ke browser localStorage menggunakan JavaScript."""
        try:
            # Use st.html with JavaScript to save to localStorage
            js_code = f"""
            <script>
                localStorage.setItem('{self.session_key}', '{json.dumps(session_data)}');
            </script>
            """
            st.html(js_code)
        except Exception as e:
            logger.error(f"Failed to save to localStorage: {e}")
            raise

    def _load_from_localstorage(self) -> bool:
        """Load session dari browser localStorage."""
        # Untuk localStorage, kita perlu JavaScript yang lebih kompleks
        # Untuk sekarang skip dulu, fokus ke URL method yang lebih reliable
        return False

    def _clear_url_session(self) -> None:
        """Clear session dari URL query parameters."""
        try:
            if self.session_key in st.query_params:
                del st.query_params[self.session_key]
        except Exception as e:
            logger.error(f"Failed to clear URL session: {e}")

    def _clear_localstorage(self) -> None:
        """Clear session dari localStorage."""
        try:
            js_code = f"""
            <script>
                localStorage.removeItem('{self.session_key}');
            </script>
            """
            st.html(js_code)
        except Exception as e:
            logger.error(f"Failed to clear localStorage: {e}")

    def _restore_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Restore session data ke session state."""
        try:
            username = session_data.get("username", "")
            email = session_data.get("email", "")
            role = session_data.get("role", "")
            signout = session_data.get("signout", True)

            if username and email and not signout:
                st.session_state.username = username
                st.session_state.useremail = email
                st.session_state.role = role
                st.session_state.signout = False
                st.session_state.last_login_time = session_data.get(
                    "timestamp", time.time())
                st.session_state._persistent_session_data = session_data
                return True

        except Exception as e:
            logger.error(f"Error restoring session data: {e}")

        return False


# Global instance
_persistent_session_manager = None


def get_persistent_session_manager() -> PersistentSessionManager:
    """Get global persistent session manager instance."""
    global _persistent_session_manager
    if _persistent_session_manager is None:
        _persistent_session_manager = PersistentSessionManager()
    return _persistent_session_manager

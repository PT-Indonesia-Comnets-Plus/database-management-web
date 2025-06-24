"""
URL-based session manager for Streamlit Cloud deployment.
This replaces the problematic cookie-based session management.
"""

import streamlit as st
import logging
import time
import uuid
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configuration constants
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600


class URLSessionManager:
    """
    URL-based session manager that uses query parameters to maintain session state.
    This is a replacement for cookie-based session management in Streamlit Cloud.
    """

    def __init__(self):
        """Initialize URL session manager."""
        self._session_key = "session_id"

    def get_session_id_from_url(self) -> Optional[str]:
        """
        Get session ID from URL query parameters.

        Returns:
            str: Session ID if found, None otherwise
        """
        try:
            query_params = st.query_params
            return query_params.get(self._session_key, None)
        except Exception as e:
            logger.error(f"Error getting session ID from URL: {e}")
            return None

    def set_session_id_in_url(self, session_id: str) -> None:
        """
        Set session ID in URL query parameters.

        Args:
            session_id: Session ID to set in URL
        """
        try:
            st.query_params[self._session_key] = session_id
            logger.info(f"Session ID set in URL: {session_id[:8]}...")
        except Exception as e:
            logger.error(f"Error setting session ID in URL: {e}")

    def clear_session_id_from_url(self) -> None:
        """Clear session ID from URL query parameters."""
        try:
            if self._session_key in st.query_params:
                del st.query_params[self._session_key]
                logger.info("Session ID cleared from URL")
        except Exception as e:
            logger.error(f"Error clearing session ID from URL: {e}")

    def generate_session_id(self) -> str:
        """
        Generate a unique session identifier.

        Returns:
            str: Unique session ID
        """
        try:
            # Create session ID based on timestamp and random component
            timestamp = str(int(time.time()))
            random_part = str(uuid.uuid4())
            session_data = f"{timestamp}_{random_part}"
            return hashlib.sha256(session_data.encode()).hexdigest()[:32]
        except Exception:
            return str(uuid.uuid4()).replace('-', '')[:32]

    def get_device_fingerprint(self) -> str:
        """
        Generate a simple device fingerprint.
        Note: This is limited in Streamlit but provides basic tracking.

        Returns:
            str: Device fingerprint
        """
        try:
            # Use session state to maintain consistency
            if 'device_fingerprint' not in st.session_state:
                # Generate based on timestamp and browser session
                fingerprint_data = f"{time.time()}_{uuid.uuid4()}"
                st.session_state.device_fingerprint = hashlib.md5(
                    fingerprint_data.encode()).hexdigest()[:16]

            return st.session_state.device_fingerprint
        except Exception:
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]

    def get_mock_ip_address(self) -> str:
        """
        Get mock IP address since real IP is not easily accessible in Streamlit.

        Returns:
            str: Mock IP address
        """
        return "127.0.0.1"  # Mock IP for Streamlit Cloud

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information (limited in Streamlit).

        Returns:
            dict: Device information
        """
        return {
            "user_agent": "Streamlit/Unknown",  # Cannot get real user agent
            "platform": "Web",
            "timestamp": datetime.now().isoformat(),
            "fingerprint": self.get_device_fingerprint()
        }

    def save_session_to_state(self, session_data: Dict[str, Any]) -> bool:
        """
        Save session data to Streamlit session state.

        Args:
            session_data: Session data to save

        Returns:
            bool: True if successful
        """
        try:
            # Save session data to session state
            for key, value in session_data.items():
                st.session_state[key] = value

            # Set session saved timestamp
            st.session_state.session_saved_at = time.time()

            logger.info("Session data saved to session state")
            return True
        except Exception as e:
            logger.error(f"Error saving session to state: {e}")
            return False

    def clear_session_from_state(self) -> bool:
        """
        Clear session data from Streamlit session state.

        Returns:
            bool: True if successful
        """
        try:
            # Keys to clear
            session_keys = [
                'username', 'useremail', 'role', 'session_id',
                'signout', 'session_expiry', 'login_timestamp',
                'session_saved_at'
            ]

            for key in session_keys:
                if key in st.session_state:
                    del st.session_state[key]

            logger.info("Session data cleared from session state")
            return True
        except Exception as e:
            logger.error(f"Error clearing session from state: {e}")
            return False

    def is_session_valid_in_state(self) -> bool:
        """
        Check if session in state is valid and not expired.

        Returns:
            bool: True if valid
        """
        try:
            # Check required fields
            required_fields = ['username', 'session_id', 'session_expiry']
            if not all(field in st.session_state for field in required_fields):
                return False

            # Check if not signed out
            if st.session_state.get('signout', True):
                return False

            # Check expiration
            session_expiry = st.session_state.get('session_expiry', 0)
            if time.time() > session_expiry:
                logger.debug("Session expired in state")
                return False

            return True
        except Exception:
            return False

    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about session manager state.

        Returns:
            dict: Debug information
        """
        return {
            'session_id_in_url': self.get_session_id_from_url(),
            'has_session_state': 'username' in st.session_state if hasattr(st, 'session_state') else False,
            'session_valid_in_state': self.is_session_valid_in_state(),
            'device_fingerprint': self.get_device_fingerprint(),
            'current_timestamp': time.time(),
            'session_expiry': st.session_state.get('session_expiry', 0) if hasattr(st, 'session_state') else 0
        }


# Global instance
_url_session_manager = None


def get_url_session_manager() -> URLSessionManager:
    """
    Get global URL session manager instance.

    Returns:
        URLSessionManager: Global instance
    """
    global _url_session_manager
    if _url_session_manager is None:
        _url_session_manager = URLSessionManager()
    return _url_session_manager


# Backward compatibility functions (for gradual migration)
def get_cookie_manager():
    """Backward compatibility - returns URL session manager."""
    logger.warning(
        "get_cookie_manager() is deprecated, use get_url_session_manager()")
    return get_url_session_manager()


def save_user_to_cookie(user_data: Dict[str, Any]) -> bool:
    """Backward compatibility - saves to session state only."""
    logger.warning("save_user_to_cookie() is deprecated")
    manager = get_url_session_manager()
    return manager.save_session_to_state(user_data)


def load_user_from_cookie() -> Optional[Dict[str, Any]]:
    """Backward compatibility - loads from session state only."""
    logger.warning("load_user_from_cookie() is deprecated")
    manager = get_url_session_manager()
    if manager.is_session_valid_in_state():
        return {
            'username': st.session_state.get('username'),
            'useremail': st.session_state.get('useremail'),
            'role': st.session_state.get('role'),
            'session_id': st.session_state.get('session_id')
        }
    return None


def clear_user_cookie() -> bool:
    """Backward compatibility - clears session state."""
    logger.warning("clear_user_cookie() is deprecated")
    manager = get_url_session_manager()
    return manager.clear_session_from_state()

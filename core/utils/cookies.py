"""
Database and URL-based session manager for Streamlit Cloud deployment.
This replaces the problematic streamlit-cookies-manager completely.
"""

import logging
import streamlit as st
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration constants
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600


def check_and_restore_persistent_session() -> bool:
    """
    Check and restore session from database using URL session ID.
    This is the main entry point for session restoration.

    Returns:
        bool: True if session was restored, False otherwise
    """
    try:
        # Get user service from session state
        user_service = st.session_state.get('user_service')
        if not user_service:
            logger.debug("UserService not available for session restoration")
            return False

        # Use UserService to restore session from database
        return user_service.restore_user_session()

    except Exception as e:
        logger.error(f"Error in session restoration: {e}")
        return False


def clear_cookies() -> bool:
    """
    Clear all session data (database and session state).

    Returns:
        bool: True if successful
    """
    try:
        # Get user service from session state
        user_service = st.session_state.get('user_service')
        if user_service:
            username = st.session_state.get('username', 'unknown')
            user_service._clear_all_sessions(username)

        # Clear session state
        for key in ['username', 'useremail', 'role', 'session_id', 'signout',
                    'login_timestamp', 'session_expiry', 'user_uid']:
            if key in st.session_state:
                del st.session_state[key]

        logger.info("All session data cleared")
        return True

    except Exception as e:
        logger.error(f"Error clearing session data: {e}")
        return False

# Backward compatibility functions (deprecated)


def get_cookie_manager():
    """Backward compatibility - returns None as cookies are no longer used."""
    logger.warning(
        "get_cookie_manager() is deprecated - session management now uses database")
    return None


def get_cloud_cookie_manager():
    """Backward compatibility - returns None as cookies are no longer used."""
    logger.warning(
        "get_cloud_cookie_manager() is deprecated - session management now uses database")
    return None


def save_user_to_cookie(user_data: Dict[str, Any]) -> bool:
    """Backward compatibility - no longer saves to cookies."""
    logger.warning(
        "save_user_to_cookie() is deprecated - sessions are now stored in database")
    return False


def load_user_from_cookie() -> Optional[Dict[str, Any]]:
    """Backward compatibility - no longer loads from cookies."""
    logger.warning(
        "load_user_from_cookie() is deprecated - sessions are now loaded from database")
    return None


def clear_user_cookie() -> bool:
    """Backward compatibility - uses new clear_cookies function."""
    logger.warning(
        "clear_user_cookie() is deprecated - use clear_cookies() instead")
    return clear_cookies()

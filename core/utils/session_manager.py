"""Session management utilities for user authentication and session validation."""

import streamlit as st
import logging
import time
from typing import Optional, Dict, Any
from .cookies import get_cloud_cookie_manager

logger = logging.getLogger(__name__)


def ensure_valid_session() -> bool:
    """
    Ensure that the current session is valid and not expired.
    Returns True if session is valid, False otherwise.
    """
    try:
        # Get current session data
        username = st.session_state.get("username", "")
        signout = st.session_state.get("signout", True)
        session_expiry = st.session_state.get("session_expiry", 0)

        # Check if session exists and is not signed out
        if not username or signout:
            logger.debug("No active session found")
            return False

        # Check if session is expired
        current_time = time.time()
        if session_expiry <= current_time:
            logger.info(f"Session expired for user: {username}")
            # Clear expired session
            clear_session()
            return False

        logger.debug(f"Valid session found for user: {username}")
        return True

    except Exception as e:
        logger.error(f"Error checking session validity: {e}")
        return False


def display_session_warning() -> None:
    """Display a warning message when session is invalid or expired."""
    st.warning("⚠️ Your session has expired or is invalid. Please log in again.")

    # Optionally add a rerun button
    if st.button("🔄 Refresh Page", key="refresh_session"):
        st.rerun()


def clear_session() -> bool:
    """Clear the current user session."""
    try:
        cookie_manager = get_cloud_cookie_manager()
        return cookie_manager.clear_user_session()
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        return False


def get_current_user() -> Optional[str]:
    """Get the current authenticated user's username."""
    try:
        if ensure_valid_session():
            return st.session_state.get("username", "")
        return None
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None


def get_current_user_role() -> Optional[str]:
    """Get the current authenticated user's role."""
    try:
        if ensure_valid_session():
            return st.session_state.get("role", "")
        return None
    except Exception as e:
        logger.error(f"Error getting current user role: {e}")
        return None


def get_session_info() -> Dict[str, Any]:
    """Get comprehensive session information."""
    try:
        return {
            "username": st.session_state.get("username", ""),
            "email": st.session_state.get("useremail", ""),
            "role": st.session_state.get("role", ""),
            "signout": st.session_state.get("signout", True),
            "login_timestamp": st.session_state.get("login_timestamp", 0),
            "session_expiry": st.session_state.get("session_expiry", 0),
            "is_valid": ensure_valid_session()
        }
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        return {
            "username": "",
            "email": "",
            "role": "",
            "signout": True,
            "login_timestamp": 0,
            "session_expiry": 0,
            "is_valid": False
        }


def refresh_session() -> bool:
    """
    Refresh the current session by extending the expiry time.
    Only works if the session is currently valid.
    """
    try:
        if not ensure_valid_session():
            logger.debug("Cannot refresh invalid session")
            return False

        # Extend session by the default timeout period
        from .cookies import SESSION_TIMEOUT_SECONDS
        new_expiry = time.time() + SESSION_TIMEOUT_SECONDS

        st.session_state.session_expiry = new_expiry

        # Update cookies if available
        cookie_manager = get_cloud_cookie_manager()
        if cookie_manager.ready:
            try:
                cookie_manager._cookies["session_expiry"] = str(new_expiry)
                cookie_manager._cookies.save()
                logger.info(
                    f"Session refreshed for user: {st.session_state.get('username')}")
            except Exception as e:
                logger.warning(f"Failed to update cookie expiry: {e}")

        return True

    except Exception as e:
        logger.error(f"Error refreshing session: {e}")
        return False


def require_authentication(redirect_to_login: bool = True) -> bool:
    """
    Decorator/function to require authentication for a page or function.

    Args:
        redirect_to_login: If True, shows login prompt when not authenticated

    Returns:
        bool: True if user is authenticated, False otherwise
    """
    try:
        if ensure_valid_session():
            return True

        if redirect_to_login:
            st.error(
                "🔒 Authentication required. Please log in to access this page.")
            display_session_warning()

        return False

    except Exception as e:
        logger.error(f"Error in require_authentication: {e}")
        return False


def is_admin() -> bool:
    """Check if the current user has admin role."""
    try:
        if not ensure_valid_session():
            return False

        role = st.session_state.get("role", "").lower()
        return role in ["admin", "administrator"]

    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


def require_admin(show_warning: bool = True) -> bool:
    """
    Require admin role for access.

    Args:
        show_warning: If True, shows warning when user is not admin

    Returns:
        bool: True if user is admin, False otherwise
    """
    try:
        if not ensure_valid_session():
            if show_warning:
                st.error("🔒 Authentication required.")
            return False

        if not is_admin():
            if show_warning:
                st.error(
                    "🚫 Admin access required. You don't have permission to access this page.")
            return False

        return True

    except Exception as e:
        logger.error(f"Error in require_admin: {e}")
        return False

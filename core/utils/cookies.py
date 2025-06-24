
"""Cookie management utilities for user session persistence."""

import streamlit as st
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)


def get_cookie_manager():
    """
    Get cookie manager instance with proper error handling for cloud deployment.
    """
    try:
        from streamlit_cookies_manager import EncryptedCookieManager

        # Get password from secrets with fallback
        cookie_password = "super_secret_key"  # Default fallback
        if hasattr(st, 'secrets'):
            cookie_password = st.secrets.get(
                "cookie_password", "super_secret_key")

        # Initialize cookies
        cookies = EncryptedCookieManager(
            prefix="Iconnet_Corp_App_v1",
            password=cookie_password
        )        # Check if cookies are ready with shorter timeout for better UX
        max_wait = 3  # seconds - reduced from 10 to 3
        start_time = time.time()

        while not cookies.ready() and (time.time() - start_time) < max_wait:
            time.sleep(0.05)  # Reduced sleep time from 0.1 to 0.05

        if not cookies.ready():
            logger.info(
                "Cookies not ready after timeout, using session-only mode")
            return None

        return cookies

    except ImportError as e:
        logger.error(f"Failed to import streamlit_cookies_manager: {e}")
        st.warning(
            "Cookie manager not available. Using session-only authentication.")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize cookie manager: {e}")
        return None


# Initialize cookies with lazy loading
_cookies_instance = None


def _get_cookies():
    """Get cookies instance with lazy loading."""
    global _cookies_instance
    if _cookies_instance is None:
        _cookies_instance = get_cookie_manager()
    return _cookies_instance


def save_user_to_cookie(username: str, email: str, role: str) -> bool:
    """Save user to cookie (matches old working code)."""
    cookies = _get_cookies()
    if cookies and cookies.ready():
        try:
            cookies["username"] = username
            cookies["email"] = email
            cookies["role"] = role
            cookies["signout"] = "False"
            cookies.save()
            logger.info(f"User {username} saved to cookies successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save user to cookies: {e}")
            # Don't show error to user, just log it
            logger.warning("Falling back to session-only authentication")
            return False
    else:
        # Fallback to session-only authentication
        logger.info("Cookies not available, using session-only authentication")
        return False


def clear_user_cookie() -> bool:
    """Clear user cookie (matches old working code)."""
    cookies = _get_cookies()
    if cookies and cookies.ready():
        cookies["username"] = ""
        cookies["email"] = ""
        cookies["role"] = ""
        cookies["signout"] = "True"
        cookies.save()

        # Clear session state immediately
        st.session_state.username = ""
        st.session_state.useremail = ""
        st.session_state.role = ""
        st.session_state.signout = True

        logger.info("User data cleared from cookies and session")
        return True

    # Fallback: clear session state only
    st.session_state.username = ""
    st.session_state.useremail = ""
    st.session_state.role = ""
    st.session_state.signout = True
    logger.info("Cookies not available, cleared session state only")
    return False


def load_cookie_to_session(session_state) -> bool:
    """Load cookie to session (matches old working code)."""
    cookies = _get_cookies()
    if cookies and cookies.ready():
        try:
            username = cookies.get("username", "") or ""
            email = cookies.get("email", "") or ""
            role = cookies.get("role", "") or ""
            signout_status = cookies.get("signout", "True")

            session_state.username = username
            session_state.useremail = email
            session_state.role = role
            session_state.signout = signout_status == "True"

            # Log successful cookie load
            if username and email and signout_status == "False":
                logger.info(
                    f"User {username} successfully loaded from cookies to session")
                return True

        except Exception as e:
            logger.error(f"Failed to load cookies to session: {e}")

    # Fallback: ensure session state has defaults
    if not hasattr(session_state, 'username'):
        session_state.username = ""
    if not hasattr(session_state, 'useremail'):
        session_state.useremail = ""
    if not hasattr(session_state, 'role'):
        session_state.role = ""
    if not hasattr(session_state, 'signout'):
        session_state.signout = True

    logger.info("Cookies not available, using session-only authentication")
    return False

# Keep the class-based approach for compatibility but use simple functions primarily


class CookieManager:
    """Centralized cookie management for user authentication state."""

    def __init__(self):
        """Initialize the encrypted cookie manager."""
        # Use the global cookies instance
        self._cookies = _get_cookies()

    @property
    def ready(self) -> bool:
        """Check if cookies are ready for use."""
        return self._cookies and self._cookies.ready() if self._cookies else False

    def is_user_authenticated(self) -> bool:
        """Check if user is authenticated based on cookies."""
        if not self.ready:
            # Fallback to session state
            return bool(st.session_state.get("username", "").strip()) and not st.session_state.get("signout", True)

        try:
            username = self._cookies.get("username", "")
            signout_status = self._cookies.get("signout", "True")
            return bool(username.strip()) and signout_status == "False"
        except Exception as e:
            logger.error(f"Error checking authentication from cookies: {e}")
            # Fallback to session state
            return bool(st.session_state.get("username", "").strip()) and not st.session_state.get("signout", True)

    def save_user(self, username: str, email: str, role: str) -> bool:
        """Save user authentication data to cookies."""
        return save_user_to_cookie(username, email, role)

    def clear_user(self) -> bool:
        """Clear user authentication data from cookies."""
        return clear_user_cookie()

    def load_to_session(self, session_state) -> bool:
        """Load user data from cookies to session state."""
        return load_cookie_to_session(session_state)

"""Cookie management utilities for user session persistence."""

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)

# Initialize cookies globally like in your old code
try:
    cookies = EncryptedCookieManager(
        prefix="Iconnet_Corp_App_v1",
        password=st.secrets.get("cookie_password", "super_secret_key")
    )

    # Check if cookies are ready
    COOKIES_AVAILABLE = cookies.ready()
    if not COOKIES_AVAILABLE:
        logger.warning("Cookies not ready, using fallback session storage")
except Exception as e:
    logger.warning(
        f"Failed to initialize cookies: {e}, using fallback session storage")
    cookies = None
    COOKIES_AVAILABLE = False


def save_user_to_cookie(username: str, email: str, role: str) -> bool:
    """Save user to cookie (with fallback handling for Streamlit Cloud)."""
    if COOKIES_AVAILABLE and cookies and cookies.ready():
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
            return False
    else:
        logger.warning(
            "Cookies not available, session data saved to session state only")
        # Update session state as fallback
        st.session_state.username = username
        st.session_state.useremail = email
        st.session_state.role = role
        st.session_state.signout = False
        return False  # Return False to indicate cookies weren't used


def clear_user_cookie() -> bool:
    """Clear user cookie (with fallback handling for Streamlit Cloud)."""
    if COOKIES_AVAILABLE and cookies and cookies.ready():
        try:
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
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            # Still clear session state even if cookies fail
            st.session_state.username = ""
            st.session_state.useremail = ""
            st.session_state.role = ""
            st.session_state.signout = True
            return False
    else:
        # Clear session state as fallback
        st.session_state.username = ""
        st.session_state.useremail = ""
        st.session_state.role = ""
        st.session_state.signout = True
        logger.warning("Cookies not available, cleared session state only")
        return False


def load_cookie_to_session(session_state) -> bool:
    """Load cookie to session (with fallback handling for Streamlit Cloud)."""
    if COOKIES_AVAILABLE and cookies and cookies.ready():
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
            else:
                logger.debug(
                    "No valid user data in cookies or user signed out")
                return False

        except Exception as e:
            logger.error(f"Failed to load cookies to session: {e}")
            # Set default values on error
            session_state.username = ""
            session_state.useremail = ""
            session_state.role = ""
            session_state.signout = True
            return False
    else:
        # Set default values when cookies not available
        if not hasattr(session_state, 'username'):
            session_state.username = ""
        if not hasattr(session_state, 'useremail'):
            session_state.useremail = ""
        if not hasattr(session_state, 'role'):
            session_state.role = ""
        if not hasattr(session_state, 'signout'):
            session_state.signout = True
        logger.debug(
            "Cookies not available, initialized default session state")
        return False

# Keep the class-based approach for compatibility but use simple functions primarily


class CookieManager:
    """Centralized cookie management for user authentication state."""

    def __init__(self):
        """Initialize the encrypted cookie manager."""
        # Use the global cookies instance
        self._cookies = cookies

    @property
    def ready(self) -> bool:
        """Check if cookies are ready for use."""
        return self._cookies.ready()

    def is_user_authenticated(self) -> bool:
        """Check if user is authenticated based on cookies."""
        if not self.ready:
            return False

        try:
            username = self._cookies.get("username", "")
            email = self._cookies.get("email", "")
            signout_str = self._cookies.get("signout", "True")

            return bool(username and email and signout_str == "False")
        except Exception as e:
            logger.error(f"Failed to check authentication status: {e}")
            return False

    def save_user(self, username: str, email: str, role: str) -> bool:
        """Save user credentials to encrypted cookies."""
        return save_user_to_cookie(username, email, role)

    def clear_user(self) -> bool:
        """Clear user data from cookies and session state."""
        return clear_user_cookie()

    def load_to_session(self, session_state) -> bool:
        """Load user data from cookies to session state."""
        return load_cookie_to_session(session_state)


# Global cookie manager instance
_cookie_manager: Optional[CookieManager] = None


def get_cookie_manager() -> CookieManager:
    """Get or create the global cookie manager instance."""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager

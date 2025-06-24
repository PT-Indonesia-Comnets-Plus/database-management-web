
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
        # Get password from secrets with secure fallback
        from streamlit_cookies_manager import EncryptedCookieManager
        cookie_password = None
        if hasattr(st, 'secrets'):
            cookie_password = st.secrets.get("cookie_password", None)

        # Use a strong default only if no secret is configured
        if not cookie_password:
            cookie_password = "ICONNET_Corp_Default_Key_2025_Please_Configure_Secrets"
            logger.warning(
                "Using default cookie password. Please configure 'cookie_password' in secrets.toml for production use")

        # Initialize cookies with the password
        cookies = EncryptedCookieManager(
            prefix="Iconnet_Corp_App_v1",
            password=cookie_password
        )        # Check if cookies are ready with adequate timeout and retry mechanism
        max_wait = 15  # seconds - increased for better stability
        retry_count = 0
        max_retries = 3
        start_time = time.time()

        while not cookies.ready() and (time.time() - start_time) < max_wait:
            time.sleep(0.1)  # Check every 100ms

            # Log progress every 5 seconds
            elapsed = time.time() - start_time
            if elapsed > 5 and retry_count == 0:
                logger.info(
                    "Cookie manager still initializing... (5s elapsed)")
                retry_count += 1
            elif elapsed > 10 and retry_count == 1:
                logger.info(
                    "Cookie manager still initializing... (10s elapsed)")
                retry_count += 1

        if not cookies.ready():
            logger.warning(
                f"Cookies not ready after {max_wait} seconds timeout, falling back to session-only mode")
            logger.info(
                "This may be due to: browser compatibility, network latency, or heavy system load")
            return None
        else:
            logger.info("Cookie manager successfully initialized")
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
    """Save user to cookie with enhanced error handling and validation."""
    try:
        # Validate inputs
        if not username or not email or not role:
            logger.error(
                "Cannot save user to cookies: missing required fields")
            return False

        cookies = _get_cookies()
        if cookies and cookies.ready():
            try:
                # Save user data to cookies
                cookies["username"] = username
                cookies["email"] = email
                cookies["role"] = role
                cookies["signout"] = "False"

                # Attempt to save with retry
                save_attempts = 0
                max_save_attempts = 3

                while save_attempts < max_save_attempts:
                    try:
                        cookies.save()
                        logger.info(
                            f"User {username} saved to cookies successfully")
                        return True
                    except Exception as save_error:
                        save_attempts += 1
                        logger.warning(
                            f"Cookie save attempt {save_attempts} failed: {save_error}")
                        if save_attempts < max_save_attempts:
                            time.sleep(0.5)  # Brief pause before retry

                logger.error(
                    f"Failed to save cookies after {max_save_attempts} attempts")
                return False

            except Exception as e:
                logger.error(f"Failed to save user to cookies: {e}")
                logger.warning("Falling back to session-only authentication")
                return False
        else:
            # Fallback to session-only authentication
            logger.info(
                "Cookies not available, using session-only authentication")
            return False

    except Exception as e:
        logger.error(f"Unexpected error in save_user_to_cookie: {e}")
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

"""Cookie management utilities for user session persistence."""

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)

# Session timeout configuration (should match UserService)
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600

# Check if running on Streamlit Cloud


def is_streamlit_cloud() -> bool:
    """Detect if running on Streamlit Cloud."""
    import os
    return (
        os.getenv("STREAMLIT_SHARING_MODE") == "1" or
        "streamlit.app" in os.getenv("HOSTNAME", "") or
        os.getenv("STREAMLIT_CLOUD_MODE") == "1" or
        "streamlit.app" in str(st.get_option("server.address"))
    )

# Initialize cookies with cloud-specific handling


def _initialize_cookies():
    """Initialize cookie manager with cloud-specific configurations."""
    try:
        # Check if we're in a proper Streamlit context
        try:
            import streamlit.runtime.scriptrunner as sr
            if sr.get_script_run_ctx() is None:
                logger.debug(
                    "Not in Streamlit context - skipping cookie initialization")
                return None, False
        except (ImportError, AttributeError):
            # If we can't check context, proceed anyway
            pass

        if is_streamlit_cloud():
            # On Streamlit Cloud, cookies might not work reliably
            logger.info(
                "Running on Streamlit Cloud - using limited cookie support")
            # Still try to initialize but with different expectations
            cookies = EncryptedCookieManager(
                prefix="Iconnet_Corp_Cloud_v1",
                password=st.secrets.get(
                    "cookie_password", "fallback_cloud_key_2025")
            )
        else:
            # Local development
            cookies = EncryptedCookieManager(
                prefix="Iconnet_Corp_App_v1",
                password=st.secrets.get("cookie_password", "super_secret_key")
            )

        # Check if cookies are ready with timeout
        import time
        start_time = time.time()
        while not cookies.ready() and (time.time() - start_time) < 3:  # 3 second timeout
            time.sleep(0.1)

        cookies_available = cookies.ready()

        if not cookies_available:
            if is_streamlit_cloud():
                logger.info(
                    "Cookies not available on Streamlit Cloud - using cloud session storage")
            else:
                logger.warning(
                    "Cookies not ready - using fallback session storage")
        else:
            logger.info("Cookie manager initialized successfully")

        return cookies, cookies_available

    except Exception as e:
        logger.warning(
            f"Failed to initialize cookies: {e} - using fallback storage")
        return None, False


# Initialize cookies globally
cookies, COOKIES_AVAILABLE = _initialize_cookies()


def save_user_to_cookie(username: str, email: str, role: str) -> bool:
    """Save user to cookie (with enhanced cloud handling)."""
    global cookies, COOKIES_AVAILABLE

    # Always save to session state as primary storage
    login_timestamp = time.time()
    st.session_state.username = username
    st.session_state.useremail = email
    st.session_state.role = role
    st.session_state.signout = False
    st.session_state.login_timestamp = login_timestamp
    st.session_state.session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS

    # Try to save to cookies as secondary storage (best effort)
    if COOKIES_AVAILABLE and cookies and cookies.ready():
        try:
            cookies["username"] = username
            cookies["email"] = email
            cookies["role"] = role
            cookies["signout"] = "False"
            cookies["login_timestamp"] = str(login_timestamp)
            cookies["session_expiry"] = str(
                login_timestamp + SESSION_TIMEOUT_SECONDS)
            cookies.save()
            logger.info(f"User {username} saved to cookies and session state")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to save to cookies, but session state saved: {e}")
            return True  # Still return True because session state worked
    else:
        if is_streamlit_cloud():
            logger.info(f"User {username} saved to session state (cloud mode)")
        else:
            logger.warning(
                f"User {username} saved to session state only (cookies unavailable)")
        return True  # Return True because session state is the primary storage


def clear_user_cookie() -> bool:
    """Clear user cookie (with enhanced cloud handling)."""
    global cookies, COOKIES_AVAILABLE

    # Always clear session state first (primary storage)
    st.session_state.username = ""
    st.session_state.useremail = ""
    st.session_state.role = ""
    st.session_state.signout = True
    if hasattr(st.session_state, 'login_timestamp'):
        del st.session_state.login_timestamp
    if hasattr(st.session_state, 'session_expiry'):
        del st.session_state.session_expiry

    # Try to clear cookies as well (best effort)
    if COOKIES_AVAILABLE and cookies and cookies.ready():
        try:
            cookies["username"] = ""
            cookies["email"] = ""
            cookies["role"] = ""
            cookies["signout"] = "True"
            cookies["login_timestamp"] = ""
            cookies["session_expiry"] = ""
            cookies.save()
            logger.info("User data cleared from cookies and session state")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to clear cookies, but session state cleared: {e}")
            return True  # Still return True because session state was cleared
    else:
        if is_streamlit_cloud():
            logger.info("User data cleared from session state (cloud mode)")
        else:
            logger.warning(
                "User data cleared from session state only (cookies unavailable)")
        return True  # Return True because session state clearing is what matters


def load_cookie_to_session(session_state) -> bool:
    """Load cookie to session (with fallback handling for Streamlit Cloud)."""
    if COOKIES_AVAILABLE and cookies and cookies.ready():
        try:
            username = cookies.get("username", "") or ""
            email = cookies.get("email", "") or ""
            role = cookies.get("role", "") or ""
            signout_status = cookies.get("signout", "True")
            login_timestamp_str = cookies.get("login_timestamp", "")
            session_expiry_str = cookies.get("session_expiry", "")

            # Parse timestamps
            login_timestamp = None
            session_expiry = None

            try:
                if login_timestamp_str:
                    login_timestamp = float(login_timestamp_str)
                if session_expiry_str:
                    session_expiry = float(session_expiry_str)
            except (ValueError, TypeError):
                logger.warning("Invalid timestamp format in cookies")
                # If we can't parse timestamps, generate new ones if user data exists
                if username and signout_status.lower() == "false":
                    current_time = time.time()
                    login_timestamp = current_time
                    # Check session expiry before loading
                    session_expiry = current_time + SESSION_TIMEOUT_SECONDS
            current_time = time.time()
            if session_expiry and current_time > session_expiry:
                logger.info(
                    f"Session expired for user {username}, clearing session")
                clear_user_cookie()
                return False

            session_state.username = username
            session_state.useremail = email
            session_state.role = role
            session_state.signout = signout_status == "True"

            # Set timestamp information
            if login_timestamp:
                session_state.login_timestamp = login_timestamp
            if session_expiry:
                session_state.session_expiry = session_expiry

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
        try:
            return self._cookies.ready() if self._cookies else False
        except Exception as e:
            logger.debug(f"Cookie ready check failed: {e}")
            return False

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
            logger.debug(f"Failed to check authentication status: {e}")
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

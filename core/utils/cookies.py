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

# Alternative storage for when cookies fail


def _save_to_browser_storage(username: str, email: str, role: str, login_timestamp: float, session_expiry: float) -> bool:
    """Fallback storage using Streamlit's session state with browser persistence."""
    try:
        # Create a browser-persistent storage key
        import hashlib
        user_hash = hashlib.md5(f"{username}_{email}".encode()).hexdigest()[:8]
        storage_key = f"iconnet_session_{user_hash}"

        session_data = {
            "username": username,
            "email": email,
            "role": role,
            "login_timestamp": login_timestamp,
            "session_expiry": session_expiry,
            "signout": False
        }

        # Save to session state with persistent key
        st.session_state[storage_key] = session_data
        logger.info(f"User {username} saved to browser storage fallback")
        return True

    except Exception as e:
        logger.warning(f"Failed to save to browser storage: {e}")
        return False


def _load_from_browser_storage(username: str, email: str) -> dict:
    """Load session data from browser storage fallback."""
    try:
        import hashlib
        user_hash = hashlib.md5(f"{username}_{email}".encode()).hexdigest()[:8]
        storage_key = f"iconnet_session_{user_hash}"

        if storage_key in st.session_state:
            return st.session_state[storage_key]
        return {}

    except Exception as e:
        logger.debug(f"Failed to load from browser storage: {e}")
        return {}

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


# Global variables for singleton pattern
_cookies_instance = None
_cookies_initialized = False
_cookies_available = False

# Initialize cookies with cloud-specific handling


def _initialize_cookies(force_reinit: bool = False):
    """Initialize cookie manager with cloud-specific configurations."""
    global _cookies_instance, _cookies_initialized, _cookies_available

    # Return cached instance if already initialized (unless forced)
    if _cookies_initialized and not force_reinit:
        return _cookies_instance, _cookies_available

    try:
        # Check if we're in a proper Streamlit context
        try:
            import streamlit.runtime.scriptrunner as sr
            if sr.get_script_run_ctx() is None:
                logger.debug(
                    "Not in Streamlit context - skipping cookie initialization")
                _cookies_initialized = True
                _cookies_available = False
                return None, False
        except (ImportError, AttributeError):
            # If we can't check context, proceed anyway
            pass

        # For simplicity, don't use unique keys - they might be causing issues
        # Use consistent keys for better reliability

        try:
            if is_streamlit_cloud():
                # On Streamlit Cloud, use a simple approach
                logger.info("Initializing cookies for Streamlit Cloud")
                cookies = EncryptedCookieManager(
                    prefix="Iconnet_Cloud",
                    password=st.secrets.get(
                        "cookie_password", "iconnet_cloud_2025")
                )
            else:
                # Local development
                logger.info("Initializing cookies for local development")
                cookies = EncryptedCookieManager(
                    prefix="Iconnet_Local",
                    password=st.secrets.get(
                        "cookie_password", "iconnet_local_key")
                )
        except Exception as e:
            logger.warning(f"Failed to initialize cookie manager: {e}")
            _cookies_initialized = True
            _cookies_available = False
            return None, False

        # Reduced timeout for faster initialization
        import time
        start_time = time.time()
        max_wait_time = 2  # Only 2 seconds

        # Simple ready check without retries to avoid hanging
        try:
            cookies_available = cookies.ready()
            if not cookies_available:
                # Give it one more second
                time.sleep(1)
                cookies_available = cookies.ready()
        except Exception as e:
            logger.debug(f"Cookie ready check failed: {e}")
            cookies_available = False

        if not cookies_available:
            logger.info("Cookies not available - using session state fallback")
        else:
            logger.info("Cookie manager initialized successfully")

        _cookies_instance = cookies if cookies_available else None
        _cookies_initialized = True
        _cookies_available = cookies_available

        return _cookies_instance, _cookies_available

    except Exception as e:
        logger.warning(
            f"Cookie initialization failed: {e} - using session state only")
        _cookies_initialized = True
        _cookies_available = False
        return None, False


# Initialize cookies globally (using singleton pattern)
_initialize_cookies()


def save_user_to_cookie(username: str, email: str, role: str) -> bool:
    """Save user to cookie (with enhanced cloud handling)."""
    global _cookies_instance, _cookies_available

    # Always save to session state as primary storage
    login_timestamp = time.time()
    st.session_state.username = username
    st.session_state.useremail = email
    st.session_state.role = role
    st.session_state.signout = False
    st.session_state.login_timestamp = login_timestamp
    # Try to save to cookies as secondary storage (best effort)
    st.session_state.session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS
    # First check if cookies are available, if not try to force re-initialize
    if not (_cookies_available and _cookies_instance):
        # Try to force re-initialize cookies for better success rate
        try:
            logger.info("Attempting to force re-initialize cookies for login")
            new_cookies, new_available = _initialize_cookies(force_reinit=True)
            if new_available and new_cookies:
                logger.info("Cookies successfully re-initialized for login")
        except Exception as e:
            logger.debug(f"Failed to force re-initialize cookies: {e}")

    if _cookies_available and _cookies_instance:
        try:
            _cookies_instance["username"] = username
            _cookies_instance["email"] = email
            _cookies_instance["role"] = role
            _cookies_instance["signout"] = "False"
            _cookies_instance["login_timestamp"] = str(login_timestamp)
            _cookies_instance["session_expiry"] = str(
                login_timestamp + SESSION_TIMEOUT_SECONDS)
            _cookies_instance.save()
            logger.info(f"User {username} saved to cookies and session state")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to save to cookies, trying fallback storage: {e}")
            # Try fallback storage
            if _save_to_browser_storage(username, email, role, login_timestamp, login_timestamp + SESSION_TIMEOUT_SECONDS):
                logger.info(
                    f"User {username} saved to fallback storage and session state")
            return True  # Still return True because session state worked
    else:
        # Try fallback storage when cookies are not available
        if _save_to_browser_storage(username, email, role, login_timestamp, login_timestamp + SESSION_TIMEOUT_SECONDS):
            logger.info(
                f"User {username} saved to fallback storage and session state")
        elif is_streamlit_cloud():
            logger.info(f"User {username} saved to session state (cloud mode)")
        else:
            logger.warning(
                f"User {username} saved to session state only (no persistence)")
        return True  # Return True because session state is the primary storage


def clear_user_cookie() -> bool:
    """Clear user cookie (with enhanced cloud handling)."""
    global _cookies_instance, _cookies_available

    # Always clear session state first (primary storage)
    st.session_state.username = ""
    st.session_state.useremail = ""
    st.session_state.role = ""
    st.session_state.signout = True
    if hasattr(st.session_state, 'login_timestamp'):
        del st.session_state.login_timestamp
    if hasattr(st.session_state, 'session_expiry'):
        del st.session_state.session_expiry
    if hasattr(st.session_state, 'user_uid'):
        del st.session_state.user_uid

    # Try to clear cookies as well (best effort)
    if _cookies_available and _cookies_instance:
        try:
            _cookies_instance["username"] = ""
            _cookies_instance["email"] = ""
            _cookies_instance["role"] = ""
            _cookies_instance["signout"] = "True"
            _cookies_instance["login_timestamp"] = ""
            _cookies_instance["session_expiry"] = ""
            _cookies_instance.save()
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
    global _cookies_instance, _cookies_available    # Try to re-initialize cookies if they weren't ready before
    # Use force re-initialization for better session restoration
    if not (_cookies_available and _cookies_instance):
        try:
            logger.info(
                "Attempting to initialize cookies for session restoration")
            new_cookies, new_available = _initialize_cookies(force_reinit=True)
            if new_available and new_cookies:
                logger.info(
                    "Cookies successfully initialized for session restoration")
        except Exception as e:
            logger.debug(
                f"Failed to initialize cookies during session load: {e}")

    if _cookies_available and _cookies_instance:
        try:
            username = _cookies_instance.get("username", "") or ""
            email = _cookies_instance.get("email", "") or ""
            role = _cookies_instance.get("role", "") or ""
            signout_status = _cookies_instance.get("signout", "True")
            login_timestamp_str = _cookies_instance.get("login_timestamp", "")
            session_expiry_str = _cookies_instance.get("session_expiry", "")

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
                login_timestamp = None
                session_expiry = None

            # If we can't parse timestamps or they don't exist, generate new ones for valid users
            if username and signout_status.lower() == "false" and (not login_timestamp or not session_expiry):
                current_time = time.time()
                login_timestamp = current_time
                session_expiry = current_time + SESSION_TIMEOUT_SECONDS
                logger.info(
                    f"Generated new session timestamps for user {username}")

                # Save the new timestamps back to cookies for consistency
                try:
                    _cookies_instance["login_timestamp"] = str(login_timestamp)
                    _cookies_instance["session_expiry"] = str(session_expiry)
                    _cookies_instance.save()
                except Exception as e:
                    logger.warning(
                        f"Failed to update timestamps in cookies: {e}")

            # Check session expiry before loading
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
        # Cookies not available, try to check if there's any existing session data
        # that might have been stored in session state from previous login
        current_username = getattr(session_state, 'username', '')
        current_email = getattr(session_state, 'useremail', '')

        if current_username and current_email:
            # Try to load from fallback storage
            fallback_data = _load_from_browser_storage(
                current_username, current_email)
            if fallback_data and not fallback_data.get('signout', True):
                # Check if session is still valid
                session_expiry = fallback_data.get('session_expiry', 0)
                if time.time() < session_expiry:
                    session_state.username = fallback_data['username']
                    session_state.useremail = fallback_data['email']
                    session_state.role = fallback_data['role']
                    session_state.signout = False
                    session_state.login_timestamp = fallback_data['login_timestamp']
                    session_state.session_expiry = fallback_data['session_expiry']
                    logger.info(
                        f"User {current_username} restored from fallback storage")
                    return True

        # Set default values when no session data available
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
        global _cookies_instance
        self._cookies = _cookies_instance

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

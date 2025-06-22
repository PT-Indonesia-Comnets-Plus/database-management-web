"""
Cookie management module for persistent login sessions.
Handles both Streamlit Cloud and local development environments.
"""

import streamlit as st
import time
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any

# Import the cookie manager
try:
    from streamlit_cookies_manager import EncryptedCookieManager
except ImportError:
    st.error("streamlit-cookies-manager is required. Please install it.")
    EncryptedCookieManager = None

logger = logging.getLogger(__name__)

# Session timeout (24 hours)
SESSION_TIMEOUT_SECONDS = 24 * 60 * 60


def _save_to_browser_storage(username: str, email: str, role: str, login_timestamp: float) -> bool:
    """Save user data to browser storage as fallback when cookies are unavailable."""
    try:
        user_hash = hashlib.md5(
            f"{username}_{email}".encode()).hexdigest()[:10]
        storage_key = f"iconnet_session_{user_hash}"

        session_data = {
            "username": username,
            "email": email,
            "role": role,
            "signout": False,
            "login_timestamp": login_timestamp,
            "session_expiry": login_timestamp + SESSION_TIMEOUT_SECONDS
        }

        # Save to session state with unique key
        st.session_state[storage_key] = session_data

        # Also save a global reference for easier lookup
        st.session_state["current_user_storage_key"] = storage_key

        logger.info(
            f"User {username} saved to browser storage fallback with key: {storage_key}")
        return True

    except Exception as e:
        logger.debug(f"Failed to save to browser storage: {e}")
        return False


def _load_from_browser_storage(username: str, email: str) -> Dict[str, Any]:
    """Load user data from browser storage fallback."""
    try:
        user_hash = hashlib.md5(
            f"{username}_{email}".encode()).hexdigest()[:10]
        storage_key = f"iconnet_session_{user_hash}"

        if storage_key in st.session_state:
            return st.session_state[storage_key]
        return {}

    except Exception as e:
        logger.debug(f"Failed to load from browser storage: {e}")
        return {}


def is_streamlit_cloud() -> bool:
    """Detect if running on Streamlit Cloud."""
    import os
    # More comprehensive cloud detection
    try:
        # Log environment info for debugging
        logger.debug(f"HOSTNAME: {os.getenv('HOSTNAME', 'Not set')}")
        logger.debug(f"PWD: {os.getenv('PWD', 'Not set')}")
        logger.debug(f"HOME: {os.getenv('HOME', 'Not set')}")

        # Check for Streamlit Cloud environment variables
        if os.getenv("STREAMLIT_SHARING_MODE") == "1":
            logger.debug("Detected cloud via STREAMLIT_SHARING_MODE")
            return True
        if os.getenv("STREAMLIT_CLOUD_MODE") == "1":
            logger.debug("Detected cloud via STREAMLIT_CLOUD_MODE")
            return True

        # Check hostname for streamlit.app
        hostname = os.getenv("HOSTNAME", "").lower()
        if "streamlit.app" in hostname:
            logger.debug(f"Detected cloud via hostname: {hostname}")
            return True

        # Check server address if available
        try:
            server_address = str(st.get_option("server.address")).lower()
            if "streamlit.app" in server_address:
                logger.debug(
                    f"Detected cloud via server address: {server_address}")
                return True
        except:
            pass

        # Check if we're running in typical cloud paths
        current_path = os.getcwd().lower()
        cloud_paths = ["/app", "/mount/src", "/home/appuser"]
        is_cloud_path = any(path in current_path for path in cloud_paths)

        if is_cloud_path:
            logger.debug(f"Detected cloud via path: {current_path}")
            return True

        # Check for Streamlit Cloud user
        if os.getenv("USER") == "appuser" or os.getenv("HOME") == "/home/appuser":
            logger.debug("Detected cloud via appuser")
            return True

        logger.debug("Local environment detected")
        return False
    except Exception as e:
        logger.debug(f"Error detecting cloud environment: {e}")
        return False


# Global variables for singleton pattern
_cookies_instance = None
_cookies_initialized = False
_cookies_available = False


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

        # Detect environment
        is_cloud = is_streamlit_cloud()
        logger.info(
            f"Environment detected: {'Streamlit Cloud' if is_cloud else 'Local Development'}")

        try:
            # Use unique key to prevent duplicate element issues
            unique_suffix = hashlib.md5(
                f"{time.time()}_{is_cloud}".encode()).hexdigest()[:8]

            if is_cloud:
                # On Streamlit Cloud, use cloud-optimized settings
                logger.info("Initializing cookies for Streamlit Cloud")
                cookies = EncryptedCookieManager(
                    prefix="IconnetCloud",
                    password=st.secrets.get(
                        "cookie_password", "iconnet_cloud_secure_2025"),
                    key=f"cloud_cookies_{unique_suffix}"
                )
            else:
                # Local development
                logger.info("Initializing cookies for local development")
                cookies = EncryptedCookieManager(
                    prefix="IconnetLocal",
                    password="iconnet_local_dev_key",
                    key=f"local_cookies_{unique_suffix}"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize cookie manager: {e}")
            _cookies_initialized = True
            _cookies_available = False
            return None, False

        # Test cookie availability with shorter timeout
        start_time = time.time()
        max_wait_time = 3  # 3 seconds max

        try:
            # Check if cookies are ready
            cookies_available = cookies.ready()

            # If not ready immediately, wait a bit
            if not cookies_available and (time.time() - start_time) < max_wait_time:
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
    st.session_state.session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS

    # Try to initialize cookies if not available
    if not (_cookies_available and _cookies_instance):
        try:
            logger.info("Attempting to initialize cookies for login")
            new_cookies, new_available = _initialize_cookies(force_reinit=True)
            if new_available and new_cookies:
                logger.info("Cookies successfully initialized for login")
        except Exception as e:
            logger.debug(f"Failed to initialize cookies: {e}")

    # Try to save to cookies as secondary storage (best effort)
    if _cookies_available and _cookies_instance:
        try:
            _cookies_instance["username"] = username
            _cookies_instance["email"] = email
            _cookies_instance["role"] = role
            _cookies_instance["signout"] = "False"
            _cookies_instance["login_timestamp"] = str(login_timestamp)
            _cookies_instance["session_expiry"] = str(
                login_timestamp + SESSION_TIMEOUT_SECONDS)

            logger.info(f"User {username} saved to cookies successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to save to cookies: {e}")

    # Fallback to browser storage
    browser_saved = _save_to_browser_storage(
        username, email, role, login_timestamp)
    if browser_saved:
        logger.info(f"User {username} saved using browser storage fallback")
        return True

    logger.info(f"User {username} saved to session state only")
    return True


def load_cookie_to_session() -> bool:
    """Load user data from cookies to session state."""
    global _cookies_instance, _cookies_available

    try:
        # Try to initialize cookies if not available
        if not (_cookies_available and _cookies_instance):
            try:
                logger.debug(
                    "Attempting to initialize cookies for session restoration")
                new_cookies, new_available = _initialize_cookies(
                    force_reinit=False)
                if new_available and new_cookies:
                    logger.debug("Cookies available for session restoration")
            except Exception as e:
                logger.debug(
                    f"Failed to initialize cookies for session restoration: {e}")

        # Strategy 1: Try cookies first
        if _cookies_available and _cookies_instance:
            try:
                username = _cookies_instance.get("username")
                email = _cookies_instance.get("email")
                role = _cookies_instance.get("role")
                signout = _cookies_instance.get("signout", "False")
                login_timestamp = _cookies_instance.get("login_timestamp")
                session_expiry = _cookies_instance.get("session_expiry")

                if username and email and role and signout == "False":
                    # Check if session is still valid
                    if session_expiry and float(session_expiry) > time.time():
                        st.session_state.username = username
                        st.session_state.useremail = email
                        st.session_state.role = role
                        st.session_state.signout = False
                        st.session_state.login_timestamp = float(
                            login_timestamp) if login_timestamp else time.time()
                        st.session_state.session_expiry = float(session_expiry)

                        logger.info(
                            f"Session restored from cookies for user: {username}")
                        return True
                    else:
                        logger.info("Cookie session expired")
            except Exception as e:
                logger.debug(f"Failed to load from cookies: {e}")

        # Strategy 2: Try browser storage with stored key
        if "current_user_storage_key" in st.session_state:
            try:
                storage_key = st.session_state["current_user_storage_key"]
                if storage_key in st.session_state:
                    fallback_data = st.session_state[storage_key]
                    if fallback_data.get("session_expiry", 0) > time.time():
                        st.session_state.username = fallback_data["username"]
                        st.session_state.useremail = fallback_data["email"]
                        st.session_state.role = fallback_data["role"]
                        st.session_state.signout = fallback_data["signout"]
                        st.session_state.login_timestamp = fallback_data["login_timestamp"]
                        st.session_state.session_expiry = fallback_data["session_expiry"]

                        logger.info(
                            f"Session restored from browser storage for user: {fallback_data['username']}")
                        return True
            except Exception as e:
                logger.debug(
                    f"Failed to load from stored browser storage: {e}")

        # Strategy 3: Search for any valid browser storage
        for key in st.session_state.keys():
            if key.startswith("iconnet_session_"):
                try:
                    fallback_data = st.session_state[key]
                    if isinstance(fallback_data, dict) and fallback_data.get("session_expiry", 0) > time.time():
                        st.session_state.username = fallback_data["username"]
                        st.session_state.useremail = fallback_data["email"]
                        st.session_state.role = fallback_data["role"]
                        st.session_state.signout = fallback_data["signout"]
                        st.session_state.login_timestamp = fallback_data["login_timestamp"]
                        st.session_state.session_expiry = fallback_data["session_expiry"]
                        st.session_state["current_user_storage_key"] = key

                        logger.info(
                            f"Session restored from browser storage search for user: {fallback_data['username']}")
                        return True
                except Exception as e:
                    logger.debug(
                        f"Failed to load from browser storage key {key}: {e}")

        # Strategy 4: Check if we already have valid session state
        if (hasattr(st.session_state, 'username') and
            hasattr(st.session_state, 'useremail') and
            hasattr(st.session_state, 'session_expiry') and
                not st.session_state.get('signout', True)):

            if st.session_state.session_expiry > time.time():
                logger.info(
                    f"Session already active for user: {st.session_state.username}")
                return True
            else:
                logger.info("Session state expired")

        logger.debug("No valid session found in any storage method")
        return False

    except Exception as e:
        logger.error(f"Error loading session: {e}")
        return False


def clear_cookies():
    """Clear all cookies and session state."""
    global _cookies_instance, _cookies_available

    try:
        # Clear cookies if available
        if _cookies_available and _cookies_instance:
            try:
                for key in ["username", "email", "role", "signout", "login_timestamp", "session_expiry"]:
                    if key in _cookies_instance:
                        del _cookies_instance[key]
                logger.info("Cookies cleared successfully")
            except Exception as e:
                logger.debug(f"Failed to clear cookies: {e}")

        # Clear session state
        for key in ["username", "useremail", "role", "signout", "login_timestamp", "session_expiry"]:
            if key in st.session_state:
                del st.session_state[key]

        # Clear browser storage fallback
        keys_to_remove = [key for key in st.session_state.keys(
        ) if key.startswith("iconnet_session_")]
        for key in keys_to_remove:
            del st.session_state[key]

        logger.info("All session data cleared")

    except Exception as e:
        logger.error(f"Error clearing session data: {e}")


def is_session_valid() -> bool:
    """Check if current session is valid."""
    try:
        if (hasattr(st.session_state, 'username') and
            hasattr(st.session_state, 'session_expiry') and
                not st.session_state.get('signout', True)):

            return st.session_state.session_expiry > time.time()
        return False
    except:
        return False


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user information if session is valid."""
    try:
        if is_session_valid():
            return {
                "username": st.session_state.get("username"),
                "email": st.session_state.get("useremail"),
                "role": st.session_state.get("role"),
                "login_timestamp": st.session_state.get("login_timestamp"),
                "session_expiry": st.session_state.get("session_expiry")
            }
        return None
    except:
        return None

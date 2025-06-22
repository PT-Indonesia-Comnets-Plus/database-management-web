"""
Cookie management module for persistent login sessions.
Handles both Streamlit Cloud and local development environments.
"""

import streamlit as st
import time
import hashlib
import logging
import base64
import json
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlencode, parse_qs

# Import the cookie manager
try:
    from streamlit_cookies_manager import EncryptedCookieManager
except ImportError:
    st.error("streamlit-cookies-manager is required. Please install it.")
    EncryptedCookieManager = None

logger = logging.getLogger(__name__)

# Session timeout (24 hours)
SESSION_TIMEOUT_SECONDS = 24 * 60 * 60


def _encode_session_data(username: str, email: str, role: str, login_timestamp: float) -> str:
    """Encode session data for URL storage."""
    try:
        session_data = {
            "u": username,  # shortened keys to reduce URL length
            "e": email,
            "r": role,
            "t": login_timestamp,
            "x": login_timestamp + SESSION_TIMEOUT_SECONDS  # expiry
        }

        # Convert to JSON and base64 encode
        json_str = json.dumps(session_data)
        encoded = base64.b64encode(json_str.encode()).decode()

        logger.debug(f"Encoded session data length: {len(encoded)} chars")
        return encoded

    except Exception as e:
        logger.error(f"Failed to encode session data: {e}")
        return ""


def _decode_session_data(encoded_data: str) -> Dict[str, Any]:
    """Decode session data from URL storage."""
    try:
        if not encoded_data:
            return {}

        # Base64 decode and parse JSON
        json_str = base64.b64decode(encoded_data.encode()).decode()
        session_data = json.loads(json_str)

        # Convert back to full format
        return {
            "username": session_data.get("u", ""),
            "email": session_data.get("e", ""),
            "role": session_data.get("r", ""),
            "login_timestamp": session_data.get("t", 0),
            "session_expiry": session_data.get("x", 0)
        }

    except Exception as e:
        logger.debug(f"Failed to decode session data: {e}")
        return {}


def _save_to_url_fallback(username: str, email: str, role: str, login_timestamp: float) -> bool:
    """Save user data to URL parameters as fallback when cookies are unavailable."""
    try:
        # Encode session data
        encoded_data = _encode_session_data(
            username, email, role, login_timestamp)
        if not encoded_data:
            return False

        # Save to session state for current session
        st.session_state["iconnet_url_session"] = encoded_data

        # Also store in a way that can be accessed by components
        st.session_state["iconnet_session_restore_data"] = {
            "username": username,
            "email": email,
            "role": role,
            "login_timestamp": login_timestamp,
            "session_expiry": login_timestamp + SESSION_TIMEOUT_SECONDS
        }

        logger.info(
            f"✅ User {username} session data prepared for URL fallback")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to save to URL fallback: {e}")
        return False


def _load_from_url_fallback() -> Dict[str, Any]:
    """Load user data from URL parameters or prepared session data."""
    try:        # First check URL parameters
        try:
            query_params = st.query_params
            if "s" in query_params:  # 's' for session
                encoded_data = query_params["s"]
                session_data = _decode_session_data(encoded_data)
                if session_data and session_data.get("session_expiry", 0) > time.time():
                    logger.debug("Found valid session in URL parameters")
                    return session_data
        except Exception as e:
            logger.debug(f"Error checking URL parameters: {e}")

        # Fallback to prepared session data
        if "iconnet_session_restore_data" in st.session_state:
            session_data = st.session_state["iconnet_session_restore_data"]
            if session_data.get("session_expiry", 0) > time.time():
                logger.debug("Found valid session in prepared data")
                return session_data

        return {}

    except Exception as e:
        logger.debug(f"Failed to load from URL fallback: {e}")
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
            pass        # Detect environment
        is_cloud = is_streamlit_cloud()
        logger.info(
            f"Environment detected: {'Streamlit Cloud' if is_cloud else 'Local Development'}")

        try:
            # Use unique prefix to prevent duplicate element issues
            unique_suffix = hashlib.md5(
                f"{time.time()}_{is_cloud}".encode()).hexdigest()[:8]

            if is_cloud:
                # On Streamlit Cloud, use cloud-optimized settings
                logger.info("Initializing cookies for Streamlit Cloud")
                cookies = EncryptedCookieManager(
                    prefix=f"IconnetCloud_{unique_suffix}",
                    password=st.secrets.get(
                        "cookie_password", "iconnet_cloud_secure_2025")
                )
            else:
                # Local development
                logger.info("Initializing cookies for local development")
                cookies = EncryptedCookieManager(
                    prefix=f"IconnetLocal_{unique_suffix}",
                    password="iconnet_local_dev_key"
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
            # Fallback to URL parameter storage
            logger.warning(f"Failed to save to cookies: {e}")
    url_saved = _save_to_url_fallback(
        username, email, role, login_timestamp)
    if url_saved:
        logger.info(f"User {username} saved using URL fallback")
        return True

    logger.info(f"User {username} saved to session state only")
    return True


def load_cookie_to_session() -> bool:
    """Load user data from cookies to session state."""
    global _cookies_instance, _cookies_available

    logger.info("=== Starting session restoration process ===")

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
                else:
                    logger.debug(
                        "Cookies not available - will use fallback methods")
            except Exception as e:
                logger.debug(
                    f"Failed to initialize cookies for session restoration: {e}")

        # Strategy 1: Try cookies first
        logger.debug("Strategy 1: Attempting cookie restoration...")
        if _cookies_available and _cookies_instance:
            try:
                username = _cookies_instance.get("username")
                email = _cookies_instance.get("email")
                role = _cookies_instance.get("role")
                signout = _cookies_instance.get("signout", "False")
                login_timestamp = _cookies_instance.get("login_timestamp")
                session_expiry = _cookies_instance.get("session_expiry")

                logger.debug(
                    f"Cookie data found: username={username}, email={email}, signout={signout}")

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
                            f"✅ Session restored from cookies for user: {username}")
                        return True
                    else:
                        logger.debug("Cookie session expired")
                else:
                    logger.debug("Incomplete cookie data")
            except Exception as e:
                logger.debug(f"Failed to load from cookies: {e}")
        else:
            logger.debug("Cookies not available")

        # Strategy 2: Try URL parameter fallback
        logger.debug("Strategy 2: Attempting URL parameter restoration...")
        try:
            fallback_data = _load_from_url_fallback()
            if fallback_data and fallback_data.get("session_expiry", 0) > time.time():
                st.session_state.username = fallback_data["username"]
                st.session_state.useremail = fallback_data["email"]
                st.session_state.role = fallback_data["role"]
                st.session_state.signout = False
                st.session_state.login_timestamp = fallback_data["login_timestamp"]
                st.session_state.session_expiry = fallback_data["session_expiry"]

                logger.info(
                    f"✅ Session restored from URL fallback for user: {fallback_data['username']}")
                return True
            else:
                logger.debug("URL fallback session expired or not found")
        except Exception as e:
            logger.debug(f"Failed to load from URL fallback: {e}")

        # Strategy 3: Check if we already have valid session state
        logger.debug("Strategy 3: Checking existing session state...")
        if (hasattr(st.session_state, 'username') and
            hasattr(st.session_state, 'useremail') and
            hasattr(st.session_state, 'session_expiry') and
                not st.session_state.get('signout', True)):

            logger.debug(
                f"Found existing session: username={st.session_state.username}, expiry={st.session_state.session_expiry}")

            if st.session_state.session_expiry > time.time():
                logger.info(
                    f"✅ Session already active for user: {st.session_state.username}")
                return True
            else:
                logger.debug("Session state expired")
        else:
            logger.debug("No valid existing session state")

        logger.info("❌ No valid session found in any storage method")
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
                # Clear session state
                logger.debug(f"Failed to clear cookies: {e}")
        for key in ["username", "useremail", "role", "signout", "login_timestamp", "session_expiry"]:
            if key in st.session_state:
                del st.session_state[key]

        # Clear URL fallback data
        for key in ["iconnet_url_session", "iconnet_session_restore_data"]:
            if key in st.session_state:
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


def get_session_url() -> str:
    """Get URL with session data for persistent login across refreshes."""
    try:
        if "iconnet_url_session" in st.session_state:
            encoded_data = st.session_state["iconnet_url_session"]
            if encoded_data:
                # Try to get the current URL from Streamlit
                try:
                    # For Streamlit Cloud, we need to build the URL differently
                    import os

                    # Check if we're on Streamlit Cloud
                    if is_streamlit_cloud():
                        # Get the app URL from environment or construct it
                        app_name = os.getenv('STREAMLIT_APP_NAME', 'app')
                        github_repo = os.getenv('GITHUB_REPOSITORY', '')

                        if github_repo:
                            # Format: https://[app-name]--[encoded-repo].streamlit.app
                            repo_encoded = github_repo.replace(
                                '/', '-').replace('_', '-').lower()
                            base_url = f"https://{app_name}--{repo_encoded}.streamlit.app"
                        else:
                            # Fallback for Streamlit Cloud
                            base_url = "https://share.streamlit.io"

                        return f"{base_url}?s={encoded_data}"
                    else:
                        # Local development
                        return f"http://localhost:8501?s={encoded_data}"

                except Exception as e:
                    logger.debug(f"Error building full URL: {e}")
                    # Fallback to relative URL
                    return f"?s={encoded_data}"

        return ""
    except Exception as e:
        logger.debug(f"Error generating session URL: {e}")
        return ""


def show_session_restore_notice():
    """Show notice about session restoration with URL."""
    try:
        # Check if we have a session URL to show
        session_url = get_session_url()
        is_valid = is_session_valid()

        if is_valid:
            with st.sidebar:
                st.success("🔒 **Login Status**: Active session")

                # Show session info
                username = st.session_state.get("username", "")
                remaining_time = st.session_state.get(
                    "session_expiry", 0) - time.time()
                remaining_hours = remaining_time / 3600 if remaining_time > 0 else 0

                if remaining_hours > 1:
                    st.info(
                        f"⏱️ Session expires in {remaining_hours:.1f} hours")
                elif remaining_hours > 0:
                    remaining_minutes = remaining_time / 60
                    st.warning(
                        f"⏱️ Session expires in {remaining_minutes:.0f} minutes")

                # Show persistent URL if available
                if session_url and "s=" in session_url:
                    st.markdown("---")
                    st.info(
                        "💡 **Persistent Login**: Bookmark this URL to stay logged in after refresh")
                    st.code(session_url, language=None)
                    st.caption(
                        "⚠️ This URL expires in 24 hours. Don't share with others.")
                else:
                    st.markdown("---")
                    st.info("💡 **Session Mode**: Cookie-based login active")
                    st.caption(
                        "Your session will persist normally with browser cookies.")
    except Exception as e:
        logger.debug(f"Error showing session restore notice: {e}")

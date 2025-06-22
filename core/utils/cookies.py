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
import os
from typing import Optional, Dict, Any

# Import performance monitoring
try:
    from .persistence_monitor import record_cookie_init, record_cookie_save, record_session_restore, record_localStorage
except ImportError:
    # Fallback functions if monitor is not available
    def record_cookie_init(success: bool): pass
    def record_cookie_save(success: bool): pass
    def record_session_restore(success: bool): pass
    def record_localStorage(success: bool): pass

# Import the cookie manager
try:
    from streamlit_cookies_manager import EncryptedCookieManager
except ImportError:
    st.error("streamlit-cookies-manager is required. Please install it.")
    EncryptedCookieManager = None

logger = logging.getLogger(__name__)

# Session timeout (24 hours)
SESSION_TIMEOUT_SECONDS = 24 * 60 * 60

# Global variables for singleton pattern
_cookies_instance = None
_cookies_initialized = False
_cookies_available = False


def is_streamlit_cloud() -> bool:
    """Detect if running on Streamlit Cloud."""
    try:
        # Check for Streamlit Cloud environment variables
        if os.getenv("STREAMLIT_SHARING_MODE") == "1":
            return True
        if os.getenv("STREAMLIT_CLOUD_MODE") == "1":
            return True

        # Check hostname for streamlit.app
        hostname = os.getenv("HOSTNAME", "").lower()
        if "streamlit.app" in hostname:
            return True

        # Check if we're running in typical cloud paths
        current_path = os.getcwd().lower()
        cloud_paths = ["/app", "/mount/src", "/home/appuser"]
        if any(path in current_path for path in cloud_paths):
            return True

        # Check for Streamlit Cloud user
        if os.getenv("USER") == "appuser" or os.getenv("HOME") == "/home/appuser":
            return True

        return False
    except Exception as e:
        logger.debug(f"Error detecting cloud environment: {e}")
        return False


def _initialize_cookies(force_reinit: bool = False):
    """Initialize cookie manager with cloud-specific configurations."""
    global _cookies_instance, _cookies_initialized, _cookies_available

    # Return cached instance if already initialized (unless forced)
    if _cookies_initialized and not force_reinit:
        return _cookies_instance, _cookies_available

    try:
        # Detect environment
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

                # Generate consistent cookie password for cloud
                try:
                    cookie_password = st.secrets.get("cookie_password")
                    if not cookie_password or len(cookie_password) < 16:
                        # Generate a consistent fallback password for cloud
                        hostname = os.getenv("HOSTNAME", "streamlit-cloud")
                        cookie_password = hashlib.sha256(
                            f"iconnet_cloud_{hostname}_2025".encode()).hexdigest()[:32]
                        logger.info(
                            "Using generated cookie password for cloud environment")
                except Exception as e:
                    # Generate a consistent fallback password
                    hostname = os.getenv("HOSTNAME", "streamlit-cloud")
                    cookie_password = hashlib.sha256(
                        f"iconnet_cloud_{hostname}_2025".encode()).hexdigest()[:32]
                    logger.warning(
                        f"Cookie password not found in secrets, using generated password: {e}")

                cookies = EncryptedCookieManager(
                    prefix=f"IconnetCloud_{unique_suffix}",
                    password=cookie_password
                )
            else:
                # Local development
                logger.info("Initializing cookies for local development")
                cookies = EncryptedCookieManager(
                    prefix=f"IconnetLocal_{unique_suffix}",
                    password="iconnet_local_dev_key_2025"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize cookie manager: {e}")
            _cookies_initialized = True
            _cookies_available = False
            record_cookie_init(False)
            return None, False

        # Test cookie availability with multiple attempts
        start_time = time.time()
        max_wait_time = 8 if is_cloud else 5
        attempt = 0
        max_attempts = 5 if is_cloud else 3

        cookies_available = False

        while not cookies_available and attempt < max_attempts and (time.time() - start_time) < max_wait_time:
            try:
                attempt += 1
                logger.debug(
                    f"Cookie availability check attempt {attempt}/{max_attempts}")

                # Check if cookies are ready
                cookies_available = cookies.ready()

                if not cookies_available:
                    # Wait between attempts
                    wait_time = min(
                        1.5 * attempt, 3.0) if is_cloud else min(1.0 * attempt, 2.0)
                    logger.debug(
                        f"Cookies not ready, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.debug("Cookies are ready!")
                    break

            except Exception as e:
                logger.debug(
                    f"Cookie ready check attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    time.sleep(1.5 if is_cloud else 1.0)

        if not cookies_available:
            logger.info(
                "Cookies not available after multiple attempts - using enhanced session state fallback")
            record_cookie_init(False)
        else:
            logger.info("✅ Cookie manager initialized successfully")
            record_cookie_init(True)

        _cookies_instance = cookies if cookies_available else None
        _cookies_initialized = True
        _cookies_available = cookies_available

        return _cookies_instance, _cookies_available

    except Exception as e:
        logger.warning(
            f"Cookie initialization failed: {e} - using session state only")
        _cookies_initialized = True
        _cookies_available = False
        record_cookie_init(False)
        return None, False


def save_user_to_cookie(username: str, email: str, role: str) -> dict:
    """Save user to cookie with enhanced persistence mechanisms."""
    global _cookies_instance, _cookies_available

    # Always save to session state as primary storage
    login_timestamp = time.time()
    st.session_state.username = username
    st.session_state.useremail = email
    st.session_state.role = role
    st.session_state.signout = False
    st.session_state.login_timestamp = login_timestamp
    st.session_state.session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS

    # Save enhanced session data for persistence
    session_data = {
        "username": username,
        "email": email,
        "role": role,
        "login_timestamp": login_timestamp,
        "session_expiry": login_timestamp + SESSION_TIMEOUT_SECONDS,
        "last_activity": time.time()
    }
    st.session_state.iconnet_persistent_session = session_data

    # Try to save to cookies
    cookies_saved = False

    # Initialize cookies if needed
    if not (_cookies_available and _cookies_instance):
        try:
            logger.info("Attempting to initialize cookies for login")
            new_cookies, new_available = _initialize_cookies(force_reinit=True)
            if new_available and new_cookies:
                _cookies_instance = new_cookies
                _cookies_available = new_available
                logger.info("Cookies successfully initialized for login")
        except Exception as e:
            logger.debug(f"Failed to initialize cookies: {e}")

    # Save to cookies if available
    if _cookies_available and _cookies_instance:
        try:
            _cookies_instance["username"] = username
            _cookies_instance["email"] = email
            _cookies_instance["role"] = role
            _cookies_instance["signout"] = "False"
            _cookies_instance["login_timestamp"] = str(login_timestamp)
            _cookies_instance["session_expiry"] = str(
                login_timestamp + SESSION_TIMEOUT_SECONDS)
            _cookies_instance["last_activity"] = str(time.time())

            logger.info(f"✅ User {username} saved to cookies successfully")
            cookies_saved = True
            record_cookie_save(True)

        except Exception as e:
            logger.warning(f"Failed to save to cookies: {e}")
            record_cookie_save(False)

    # Add JavaScript localStorage fallback for cloud environments
    js_fallback_added = False
    try:
        if is_streamlit_cloud():
            # Create enhanced localStorage implementation
            session_data_encoded = base64.b64encode(
                json.dumps(session_data).encode()).decode()

            js_code = f"""
            <script>
            try {{
                const sessionData = '{session_data_encoded}';
                const timestamp = '{time.time()}';
                
                // Save to localStorage
                localStorage.setItem('iconnet_session', sessionData);
                localStorage.setItem('iconnet_session_timestamp', timestamp);
                localStorage.setItem('iconnet_session_username', '{username}');
                
                // Also save to sessionStorage as backup
                sessionStorage.setItem('iconnet_session', sessionData);
                sessionStorage.setItem('iconnet_session_timestamp', timestamp);
                
                console.log('✅ Session saved to localStorage and sessionStorage');
                
                // Set up periodic refresh to maintain session
                if (!window.iconnetSessionKeepAlive) {{
                    window.iconnetSessionKeepAlive = setInterval(() => {{
                        try {{
                            localStorage.setItem('iconnet_session_timestamp', Date.now() / 1000);
                            console.log('🔄 Session timestamp updated');
                        }} catch (e) {{
                            console.error('Failed to update session timestamp:', e);
                        }}
                    }}, 60000); // Update every minute
                }}
                
            }} catch (e) {{
                console.error('❌ Failed to save to localStorage:', e);
                
                // Try alternative storage methods
                try {{
                    sessionStorage.setItem('iconnet_session_fallback', sessionData);
                    console.log('⚠️ Fallback to sessionStorage only');
                }} catch (e2) {{
                    console.error('❌ All storage methods failed:', e2);
                }}
            }}
            </script>
            """

            st.components.v1.html(js_code, height=0)
            js_fallback_added = True
            record_localStorage(True)
            logger.info(
                f"Enhanced localStorage fallback added for user {username}")

    except Exception as e:
        logger.debug(f"Failed to add JavaScript fallback: {e}")
        record_localStorage(False)

    # Determine method and return result
    if cookies_saved and js_fallback_added:
        method = 'hybrid'
    elif cookies_saved:
        method = 'cookies'
    elif js_fallback_added:
        method = 'session_with_js'
    else:
        method = 'session_only'
        logger.info(f"User {username} saved to session state only")

    return {
        'success': True,
        'method': method,
        'requires_url_click': False
    }


def load_cookie_to_session() -> bool:
    """Load user data from multiple persistence sources."""
    global _cookies_instance, _cookies_available

    logger.info("=== Starting enhanced session restoration process ===")

    try:
        # Try to initialize cookies if not available
        if not (_cookies_available and _cookies_instance):
            try:
                logger.debug(
                    "Attempting to initialize cookies for session restoration")
                new_cookies, new_available = _initialize_cookies(
                    force_reinit=False)
                if new_available and new_cookies:
                    _cookies_instance = new_cookies
                    _cookies_available = new_available
                    logger.debug("Cookies available for session restoration")
                else:
                    logger.debug("Cookies not available")
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

                if username and email and role and signout == "False":
                    if session_expiry and float(session_expiry) > time.time():
                        # Update last activity in cookies
                        try:
                            _cookies_instance["last_activity"] = str(
                                time.time())
                        except:
                            pass

                        # Restore to session state
                        st.session_state.username = username
                        st.session_state.useremail = email
                        st.session_state.role = role
                        st.session_state.signout = False
                        st.session_state.login_timestamp = float(
                            login_timestamp) if login_timestamp else time.time()
                        st.session_state.session_expiry = float(session_expiry)
                        st.session_state.iconnet_persistent_session = {
                            "username": username,
                            "email": email,
                            "role": role,
                            "login_timestamp": float(login_timestamp) if login_timestamp else time.time(),
                            "session_expiry": float(session_expiry),
                            "last_activity": time.time()
                        }

                        logger.info(
                            f"✅ Session restored from cookies for user: {username}")
                        record_session_restore(True)
                        return True
                    else:
                        logger.debug("Cookie session expired")
                        try:
                            _cookies_instance["signout"] = "True"
                        except:
                            pass
                else:
                    logger.debug("Incomplete cookie data")
            except Exception as e:
                logger.debug(f"Failed to load from cookies: {e}")
        else:
            logger.debug("Cookies not available")

        # Strategy 2: Check if we already have valid session state
        logger.debug("Strategy 2: Checking existing session state...")
        if (hasattr(st.session_state, 'username') and
            hasattr(st.session_state, 'useremail') and
            hasattr(st.session_state, 'session_expiry') and
                not st.session_state.get('signout', True)):

            if st.session_state.session_expiry > time.time():
                logger.info(
                    f"✅ Session already active for user: {st.session_state.username}")
                return True
            else:
                logger.debug("Session state expired")
                st.session_state.signout = True
        else:
            logger.debug("No valid existing session state")

        # Strategy 3: Check persistent session data
        logger.debug("Strategy 3: Checking persistent session data...")
        if "iconnet_persistent_session" in st.session_state:
            session_data = st.session_state.iconnet_persistent_session
            if (session_data.get("session_expiry", 0) > time.time() and
                    session_data.get("username") and session_data.get("email")):

                st.session_state.username = session_data["username"]
                st.session_state.useremail = session_data["email"]
                st.session_state.role = session_data["role"]
                st.session_state.signout = False
                st.session_state.login_timestamp = session_data["login_timestamp"]
                st.session_state.session_expiry = session_data["session_expiry"]

                logger.info(
                    f"✅ Session restored from persistent data for user: {session_data['username']}")
                record_session_restore(True)
                return True

        logger.info("❌ No valid session found - user needs to login")
        record_session_restore(False)
        return False

    except Exception as e:
        logger.error(f"Error during session restoration: {e}")
        record_session_restore(False)
        return False


def clear_cookies():
    """Clear all cookies and session state with enhanced cleanup."""
    global _cookies_instance, _cookies_available

    try:
        # Clear cookies if available
        if _cookies_available and _cookies_instance:
            try:
                # Set signout flag first
                _cookies_instance["signout"] = "True"

                # Then clear all session keys
                for key in ["username", "email", "role", "login_timestamp", "session_expiry", "last_activity"]:
                    if key in _cookies_instance:
                        del _cookies_instance[key]
                logger.info("Cookies cleared successfully")
            except Exception as e:
                logger.debug(f"Failed to clear cookies: {e}")

        # Clear session state
        for key in ["username", "useremail", "role", "signout", "login_timestamp", "session_expiry"]:
            if key in st.session_state:
                del st.session_state[key]

        # Clear enhanced session data
        for key in ["iconnet_persistent_session", "iconnet_localStorage_session"]:
            if key in st.session_state:
                del st.session_state[key]

        # Clear localStorage via JavaScript (for cloud environments)
        if is_streamlit_cloud():
            try:
                js_code = """
                <script>
                try {
                    localStorage.removeItem('iconnet_session');
                    localStorage.removeItem('iconnet_session_timestamp');
                    localStorage.removeItem('iconnet_session_username');
                    sessionStorage.removeItem('iconnet_session');
                    sessionStorage.removeItem('iconnet_session_timestamp');
                    sessionStorage.removeItem('iconnet_session_fallback');
                    
                    // Clear keepalive interval
                    if (window.iconnetSessionKeepAlive) {
                        clearInterval(window.iconnetSessionKeepAlive);
                        window.iconnetSessionKeepAlive = null;
                    }
                    
                    console.log('✅ Session data cleared from localStorage and sessionStorage');
                } catch (e) {
                    console.error('Failed to clear storage:', e);
                }
                </script>
                """
                st.components.v1.html(js_code, height=0)
                logger.info("JavaScript storage cleanup executed")
            except Exception as e:
                logger.debug(f"Failed to clear JavaScript storage: {e}")

        # Force session state signout
        st.session_state.signout = True

        logger.info("All session data cleared comprehensively")

    except Exception as e:
        logger.error(f"Error clearing session data: {e}")
        # Ensure signout is set even if clearing fails
        st.session_state.signout = True


def is_session_valid() -> bool:
    """Check if current session is valid."""
    try:
        if (hasattr(st.session_state, 'username') and
            hasattr(st.session_state, 'session_expiry') and
                not st.session_state.get('signout', True)):

            return st.session_state.session_expiry > time.time()
        return False
    except Exception:
        return False


def update_session_activity():
    """Update session activity timestamp to keep session alive."""
    try:
        current_time = time.time()

        # Update session state
        if hasattr(st.session_state, 'username') and not st.session_state.get('signout', True):
            st.session_state.last_activity = current_time

            # Update persistent session data
            if "iconnet_persistent_session" in st.session_state:
                st.session_state.iconnet_persistent_session["last_activity"] = current_time

            # Update cookies if available
            global _cookies_instance, _cookies_available
            if _cookies_available and _cookies_instance:
                try:
                    _cookies_instance["last_activity"] = str(current_time)
                except Exception as e:
                    logger.debug(f"Failed to update cookie activity: {e}")

    except Exception as e:
        logger.debug(f"Failed to update session activity: {e}")


def setup_session_heartbeat():
    """Setup automatic session heartbeat to maintain session persistence."""
    try:
        # Only setup heartbeat if user is logged in
        if (hasattr(st.session_state, 'username') and
            st.session_state.username and
                not st.session_state.get('signout', True)):

            # Update activity every time this is called
            update_session_activity()

    except Exception as e:
        logger.debug(f"Failed to setup session heartbeat: {e}")


def check_session_timeout() -> bool:
    """Check if current session has timed out."""
    try:
        if not hasattr(st.session_state, 'session_expiry'):
            return True

        current_time = time.time()
        session_expiry = st.session_state.session_expiry

        if current_time > session_expiry:
            logger.info("Session has expired")
            clear_cookies()
            return True

        return False

    except Exception as e:
        logger.error(f"Error checking session timeout: {e}")
        return True


# Placeholder functions for compatibility
def show_session_restore_notice():
    """Show session restore notice (placeholder)."""
    pass


def get_session_debug_info() -> dict:
    """Get session debug information."""
    try:
        return {
            'environment': 'Cloud' if is_streamlit_cloud() else 'Local',
            'cookies_available': _cookies_available,
            'cookies_initialized': _cookies_initialized,
            'session_state_keys': list(st.session_state.keys()) if hasattr(st, 'session_state') else [],
            'has_persistent_session': 'iconnet_persistent_session' in st.session_state if hasattr(st, 'session_state') else False,
            'is_authenticated': bool(st.session_state.get('username')) if hasattr(st, 'session_state') else False,
            'session_expiry': st.session_state.get('session_expiry', 0) if hasattr(st, 'session_state') else 0,
            'current_time': time.time()
        }
    except Exception as e:
        logger.error(f"Error getting session debug info: {e}")
        return {}


def display_session_debug_info():
    """Display session debug information in Streamlit."""
    try:
        debug_info = get_session_debug_info()

        if debug_info:
            st.write("**Session Debug Info:**")
            for key, value in debug_info.items():
                if key == 'session_state_keys':
                    st.write(f"- {key}: {len(value)} keys")
                elif key == 'session_expiry' and value > 0:
                    remaining = max(0, value - time.time())
                    st.write(f"- {key}: {remaining/3600:.2f} hours remaining")
                else:
                    st.write(f"- {key}: {value}")
    except Exception as e:
        logger.error(f"Error displaying session debug info: {e}")
        st.error(f"Debug info error: {e}")


# Export all functions
__all__ = [
    'save_user_to_cookie',
    'load_cookie_to_session',
    'clear_cookies',
    'is_session_valid',
    'is_streamlit_cloud',
    'update_session_activity',
    'setup_session_heartbeat',
    'check_session_timeout',
    'show_session_restore_notice',
    'get_session_debug_info',
    'display_session_debug_info'
]

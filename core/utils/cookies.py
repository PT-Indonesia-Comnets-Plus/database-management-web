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
    try:
        # First check URL parameters
        try:
            query_params = st.query_params
            logger.debug(f"Query params: {dict(query_params)}")

            if "s" in query_params:  # 's' for session
                encoded_data = query_params["s"]
                logger.debug(
                    f"Found session data in URL: {encoded_data[:50]}...")
                session_data = _decode_session_data(encoded_data)
                logger.debug(f"Decoded session data: {session_data}")

                if session_data and session_data.get("session_expiry", 0) > time.time():
                    logger.info("✅ Found valid session in URL parameters")
                    return session_data
                else:
                    logger.debug("❌ URL session data expired or invalid")
            else:
                logger.debug("❌ No 's' parameter found in URL")
        except Exception as e:
            logger.debug(f"❌ Error checking URL parameters: {e}")

        # Fallback to prepared session data
        if "iconnet_session_restore_data" in st.session_state:
            session_data = st.session_state["iconnet_session_restore_data"]
            logger.debug(f"Found prepared session data: {session_data}")
            if session_data.get("session_expiry", 0) > time.time():
                logger.info("✅ Found valid session in prepared data")
                return session_data
            else:
                logger.debug("❌ Prepared session data expired")
        else:
            logger.debug("❌ No prepared session data found")

        return {}

    except Exception as e:
        logger.debug(f"❌ Failed to load from URL fallback: {e}")
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
            # Use unique prefix to prevent duplicate element issues
            unique_suffix = hashlib.md5(
                f"{time.time()}_{is_cloud}".encode()).hexdigest()[:8]

            if is_cloud:
                # On Streamlit Cloud, use cloud-optimized settings
                logger.info("Initializing cookies for Streamlit Cloud")

                # Try to get cookie password from secrets
                try:
                    cookie_password = st.secrets.get(
                        "cookie_password", "iconnet_cloud_secure_2025")
                    if len(cookie_password) < 16:
                        cookie_password = "iconnet_cloud_secure_2025_fallback_key"
                except Exception:
                    cookie_password = "iconnet_cloud_secure_2025_fallback_key"

                cookies = EncryptedCookieManager(
                    prefix=f"IconnetCloud_{unique_suffix}",
                    password=cookie_password,
                    # Add cloud-specific settings
                    auto_renewal=True,
                    domain=None,
                    path="/",
                    samesite="Lax",  # More permissive for cloud
                    secure=True
                )
            else:
                # Local development
                logger.info("Initializing cookies for local development")
                cookies = EncryptedCookieManager(
                    prefix=f"IconnetLocal_{unique_suffix}",
                    password="iconnet_local_dev_key_2025",
                    auto_renewal=True
                )
        except Exception as e:
            logger.warning(f"Failed to initialize cookie manager: {e}")
            _cookies_initialized = True
            _cookies_available = False
            return None, False

        # Test cookie availability with multiple attempts for better reliability
        start_time = time.time()
        max_wait_time = 8 if is_cloud else 5  # More time for cloud
        attempt = 0
        max_attempts = 5 if is_cloud else 3  # More attempts for cloud

        cookies_available = False

        while not cookies_available and attempt < max_attempts and (time.time() - start_time) < max_wait_time:
            try:
                attempt += 1
                logger.debug(
                    f"Cookie availability check attempt {attempt}/{max_attempts}")

                # Check if cookies are ready
                cookies_available = cookies.ready()

                if not cookies_available:
                    # Wait between attempts, with increasing delay
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
        return None, False


def save_user_to_cookie(username: str, email: str, role: str) -> dict:
    """Save user to cookie with enhanced persistence mechanisms.

    Returns:
        dict: {
            'success': bool,
            'method': str ('cookies', 'hybrid', 'session_with_js'),
            'requires_url_click': bool
        }
    """
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

    # Try to save to cookies - simplified approach
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
            # Save basic session data
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
            # Create JavaScript code to save to localStorage
            session_data_encoded = base64.b64encode(
                json.dumps(session_data).encode()
            ).decode()

            js_code = f"""
            <script>
            // Save session data to localStorage
            try {{
                const sessionData = '{session_data_encoded}';
                localStorage.setItem('iconnet_session', sessionData);
                localStorage.setItem('iconnet_session_timestamp', '{time.time()}');
                console.log('Session saved to localStorage');
                
                // Also try to save to sessionStorage as backup
                sessionStorage.setItem('iconnet_session', sessionData);
                sessionStorage.setItem('iconnet_session_timestamp', '{time.time()}');
                
            }} catch (e) {{
                console.error('Failed to save to localStorage:', e);
            }}
            </script>
            """

            # Add the JavaScript code to the page            st.components.v1.html(js_code, height=0)
            js_fallback_added = True
            record_localStorage(True)
            logger.info(
                f"JavaScript localStorage fallback added for user {username}")

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
    """Load user data from multiple persistence sources - ENHANCED VERSION."""
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

        # Strategy 1: Try cookies first (MAIN METHOD)
        logger.debug("Strategy 1: Attempting cookie restoration...")
        if _cookies_available and _cookies_instance:
            try:
                username = _cookies_instance.get("username")
                email = _cookies_instance.get("email")
                role = _cookies_instance.get("role")
                signout = _cookies_instance.get("signout", "False")
                login_timestamp = _cookies_instance.get("login_timestamp")
                session_expiry = _cookies_instance.get("session_expiry")
                last_activity = _cookies_instance.get("last_activity")

                logger.debug(
                    f"Cookie data found: username={username}, email={email}, signout={signout}")

                if username and email and role and signout == "False":
                    # Check if session is still valid
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
                        # Clear expired cookies
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

        # Strategy 2: Try JavaScript localStorage (for cloud environments)
        logger.debug("Strategy 2: Attempting localStorage restoration...")
        if is_streamlit_cloud():
            try:
                # Create JavaScript to read from localStorage
                js_code = """
                <script>
                try {
                    const sessionData = localStorage.getItem('iconnet_session');
                    const timestamp = localStorage.getItem('iconnet_session_timestamp');
                    
                    if (sessionData && timestamp) {
                        // Post message to parent (Streamlit)
                        const data = {
                            type: 'iconnet_session_data',
                            sessionData: sessionData,
                            timestamp: timestamp
                        };
                        
                        // Try multiple ways to communicate with Streamlit
                        if (window.parent) {
                            window.parent.postMessage(data, '*');
                        }
                        if (window.top) {
                            window.top.postMessage(data, '*');
                        }
                        
                        console.log('Posted session data to Streamlit');
                    } else {
                        console.log('No session data found in localStorage');
                    }
                } catch (e) {
                    console.error('Failed to read from localStorage:', e);
                }
                </script>
                """

                # Add message listener (this is a placeholder - in real implementation
                # you'd need to use streamlit-js-communication or similar)
                st.components.v1.html(js_code, height=0)

                # Check if we have session data from a previous page load
                if "iconnet_js_session_data" in st.session_state:
                    session_data = st.session_state.iconnet_js_session_data

                    if (session_data.get("session_expiry", 0) > time.time() and
                            session_data.get("username") and session_data.get("email")):

                        st.session_state.username = session_data["username"]
                        st.session_state.useremail = session_data["email"]
                        st.session_state.role = session_data["role"]
                        st.session_state.signout = False
                        st.session_state.login_timestamp = session_data["login_timestamp"]
                        st.session_state.session_expiry = session_data["session_expiry"]
                        st.session_state.iconnet_persistent_session = session_data

                        logger.info(
                            f"✅ Session restored from localStorage for user: {session_data['username']}")
                        return True

            except Exception as e:
                logger.debug(f"Failed to load from localStorage: {e}")

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
                # Clear expired session
                st.session_state.signout = True
        else:
            logger.debug("No valid existing session state")

        # Strategy 4: Check persistent session data
        logger.debug("Strategy 4: Checking persistent session data...")
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
                return True
            logger.info("❌ No valid session found - user needs to login")
        record_session_restore(False)
        return False

    except Exception as e:
        logger.error(f"Error during session restoration: {e}")
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
        for key in ["iconnet_persistent_session", "iconnet_js_session_data", "iconnet_url_session", "iconnet_session_restore_data"]:
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
                    sessionStorage.removeItem('iconnet_session');
                    sessionStorage.removeItem('iconnet_session_timestamp');
                    console.log('Session data cleared from localStorage and sessionStorage');
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
        logger.debug("🔍 Checking for session URL generation...")

        if "iconnet_url_session" in st.session_state:
            encoded_data = st.session_state["iconnet_url_session"]
            logger.debug(f"Found session data: {encoded_data[:50]}...")

            if encoded_data:
                # Simple approach: just use relative URL with session parameter
                # This will work on both local and Streamlit Cloud
                session_url = f"?s={encoded_data}"
                logger.debug(f"✅ Generated session URL: {session_url}")
                return session_url
        else:
            logger.debug("❌ No session data found in session state")

        return ""
    except Exception as e:
        logger.error(f"❌ Error generating session URL: {e}")
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


def show_persistent_login_prompt():
    """Show persistent login prompt after URL fallback is used."""
    try:
        logger.info("🔗 Showing persistent login prompt...")

        # Check directly for session data instead of relying on get_session_url()
        if "iconnet_url_session" in st.session_state:
            encoded_data = st.session_state["iconnet_url_session"]
            logger.debug(f"Found session data: {encoded_data[:50]}...")

            if encoded_data:
                # Create the session URL
                session_url = f"?s={encoded_data}"
                logger.info("✅ Displaying persistent login link to user")

                # Show prominent message to user
                st.success("🎉 **Login Successful!**")
                st.info(
                    "🔗 **CRITICAL**: To enable persistent login, you **MUST** click the link below:")

                # Create a very visible clickable link
                st.markdown(
                    f"## � [**🔗 CLICK HERE FOR PERSISTENT LOGIN**]({session_url})")

                st.error(
                    "⚠️ **WARNING**: If you don't click the link above, you'll need to login again after page refresh!")
                st.caption(
                    "💡 After clicking, your browser URL will change to include session data.")

                # Also show it in a code block for copying
                with st.expander("📋 Manual URL (copy if needed)"):
                    st.code(session_url, language=None)
                    st.caption(
                        "You can also copy this URL and paste it in your browser.")

                return True
            else:
                logger.warning("❌ Session data is empty")
        else:
            logger.warning("❌ No 'iconnet_url_session' found in session state")

        # Fallback message if no session URL available
        st.warning(
            "⚠️ Persistent login not available. You may need to login again after page refresh.")
        return False

    except Exception as e:
        logger.error(f"❌ Error showing persistent login prompt: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Session activity tracking functions


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

            # Update localStorage if in cloud
            if is_streamlit_cloud():
                try:
                    session_data = st.session_state.get(
                        "iconnet_persistent_session", {})
                    if session_data:
                        session_data_encoded = base64.b64encode(
                            json.dumps(session_data).encode()
                        ).decode()

                        js_code = f"""
                        <script>
                        try {{
                            localStorage.setItem('iconnet_session', '{session_data_encoded}');
                            localStorage.setItem('iconnet_session_timestamp', '{current_time}');
                        }} catch (e) {{
                            console.error('Failed to update localStorage activity:', e);
                        }}
                        </script>
                        """
                        st.components.v1.html(js_code, height=0)
                except Exception as e:
                    logger.debug(
                        f"Failed to update localStorage activity: {e}")

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

            # Add a heartbeat JavaScript that runs periodically
            if is_streamlit_cloud():
                js_code = """
                <script>
                // Session heartbeat for Streamlit Cloud
                function iconnetHeartbeat() {
                    try {
                        const currentTime = Date.now() / 1000;
                        const sessionData = localStorage.getItem('iconnet_session');
                        
                        if (sessionData) {
                            // Update timestamp in localStorage
                            localStorage.setItem('iconnet_session_timestamp', currentTime.toString());
                            
                            // Parse and update the session data
                            const decoded = atob(sessionData);
                            const sessionObj = JSON.parse(decoded);
                            sessionObj.last_activity = currentTime;
                            
                            const encoded = btoa(JSON.stringify(sessionObj));
                            localStorage.setItem('iconnet_session', encoded);
                        }
                    } catch (e) {
                        console.error('Heartbeat failed:', e);
                    }
                }
                
                // Run heartbeat every 5 minutes
                if (!window.iconnetHeartbeatInterval) {
                    window.iconnetHeartbeatInterval = setInterval(iconnetHeartbeat, 5 * 60 * 1000);
                    console.log('Session heartbeat started');
                }
                </script>
                """
                st.components.v1.html(js_code, height=0)

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

        # Also check if session is close to expiring (within 30 minutes)
        time_until_expiry = session_expiry - current_time
        if time_until_expiry < 1800:  # 30 minutes
            logger.info(
                f"Session expires in {time_until_expiry/60:.1f} minutes")

        return False

    except Exception as e:
        logger.error(f"Error checking session timeout: {e}")
        return True


# Debug and monitoring functions

def get_session_debug_info() -> dict:
    """Get comprehensive session debug information."""
    global _cookies_instance, _cookies_available

    try:
        debug_info = {
            "timestamp": time.time(),
            "environment": "cloud" if is_streamlit_cloud() else "local",
            "cookies_available": _cookies_available,
            "cookies_initialized": _cookies_initialized,
            "session_state": {},
            "cookies_data": {},
            "persistent_data": {},
            "errors": []
        }

        # Session state info
        try:
            for key in ["username", "useremail", "role", "signout", "login_timestamp", "session_expiry"]:
                if hasattr(st.session_state, key):
                    debug_info["session_state"][key] = getattr(
                        st.session_state, key)
        except Exception as e:
            debug_info["errors"].append(f"Failed to read session state: {e}")

        # Cookies info
        try:
            if _cookies_available and _cookies_instance:
                for key in ["username", "email", "role", "signout", "login_timestamp", "session_expiry", "last_activity"]:
                    if key in _cookies_instance:
                        debug_info["cookies_data"][key] = _cookies_instance[key]
        except Exception as e:
            debug_info["errors"].append(f"Failed to read cookies: {e}")

        # Persistent data info
        try:
            if "iconnet_persistent_session" in st.session_state:
                debug_info["persistent_data"] = st.session_state.iconnet_persistent_session
        except Exception as e:
            debug_info["errors"].append(f"Failed to read persistent data: {e}")

        return debug_info

    except Exception as e:
        return {"error": f"Failed to generate debug info: {e}"}


def log_session_status():
    """Log current session status for debugging."""
    try:
        debug_info = get_session_debug_info()
        logger.info(
            f"Session Status Debug: {json.dumps(debug_info, indent=2, default=str)}")
        return debug_info
    except Exception as e:
        logger.error(f"Failed to log session status: {e}")
        return None


def display_session_debug_info():
    """Display session debug information in Streamlit (for development)."""
    try:
        if st.secrets.get("debug_mode", False) or not is_streamlit_cloud():
            with st.expander("🔍 Session Debug Info", expanded=False):
                debug_info = get_session_debug_info()
                st.json(debug_info)

                if st.button("Refresh Debug Info"):
                    st.rerun()

                if st.button("Force Session Cleanup"):
                    clear_cookies()
                    st.success("Session cleared!")
                    st.rerun()

    except Exception as e:
        logger.debug(f"Failed to display debug info: {e}")


# Export all functions for easy importing
__all__ = [
    'save_user_to_cookie',
    'load_cookie_to_session',
    'clear_cookies',
    'is_session_valid',
    'is_streamlit_cloud',
    'update_session_activity',
    'setup_session_heartbeat',
    'check_session_timeout',
    'get_session_debug_info',
    'log_session_status',
    'display_session_debug_info'
]

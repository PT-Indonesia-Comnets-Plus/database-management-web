"""Cookie management utilities for user session persistence - Streamlit Cloud Optimized."""

import streamlit as st
from typing import Optional, Dict, Any
import time
import logging
import os
import json
import hashlib

# Import required for cookie functionality
try:
    from streamlit_cookies_manager import EncryptedCookieManager
    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False
    EncryptedCookieManager = None

# Import new Streamlit Cloud session manager
try:
    from .streamlit_cloud_cookies import (
        get_streamlit_cloud_session_manager,
        save_user_session_cloud,
        load_user_session_cloud,
        clear_user_session_cloud,
        is_user_authenticated_cloud
    )
    CLOUD_COOKIES_AVAILABLE = True
except ImportError:
    CLOUD_COOKIES_AVAILABLE = False
    # logger will be defined after this block

logger = logging.getLogger(__name__)

# Session timeout configuration (should match UserService)
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600

# Global cookie manager to prevent multiple instances
_global_cookie_manager = None
_cookie_init_attempted = False


def is_streamlit_cloud() -> bool:
    """Detect if running on Streamlit Cloud with enhanced detection."""
    try:
        cloud_indicators = [
            os.getenv("STREAMLIT_SHARING_MODE") == "1",
            os.getenv("STREAMLIT_CLOUD_MODE") == "1",
            "streamlit.app" in os.getenv("HOSTNAME", ""),
            "streamlit.app" in os.getenv("SERVER_NAME", ""),
            "/mount/src/" in os.getcwd(),
            os.path.exists("/.dockerenv")
        ]

        try:
            server_address = str(st.get_option("server.address") or "")
            if "streamlit.app" in server_address or "0.0.0.0" in server_address:
                cloud_indicators.append(True)
        except Exception:
            pass

        return any(cloud_indicators)
    except Exception:
        return False


class StreamlitCloudCookieManager:
    """
    Streamlit Cloud optimized cookie manager that handles session persistence
    with fallbacks for when cookies are not available.
    """

    def __init__(self):
        """Initialize the cookie manager with cloud-specific optimizations."""
        self._cookies = None
        self._ready = False
        self._session_key = f"cloud_session_{self._get_session_hash()}"
        self._init_attempted = False

    def _get_session_hash(self) -> str:
        """Generate a unique session hash for this session."""
        try:
            # Use session info to create unique hash
            session_info = {
                # Changes every hour
                'timestamp': str(int(time.time() / 3600)),
                'user_agent': st.context.headers.get('User-Agent', 'unknown')[:50] if hasattr(st, 'context') and hasattr(st.context, 'headers') else 'unknown'
            }
            session_str = json.dumps(session_info, sort_keys=True)
            return hashlib.md5(session_str.encode()).hexdigest()[:12]
        except Exception:
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

    def _initialize_cookies(self) -> bool:
        """Initialize cookies with proper error handling and unique keys."""
        if self._init_attempted:
            return self._ready

        self._init_attempted = True

        try:
            # Skip if cookies library not available
            if not COOKIES_AVAILABLE or EncryptedCookieManager is None:
                logger.info(
                    "streamlit-cookies-manager not available, using session state only")
                return False

            # Check if we're in proper Streamlit context
            try:
                import streamlit.runtime.scriptrunner as sr
                if sr.get_script_run_ctx() is None:
                    logger.debug(
                        "Not in Streamlit context - using session state only")
                    return False
            except (ImportError, AttributeError):
                pass

            # For Streamlit Cloud, use simpler prefix to avoid conflicts
            if is_streamlit_cloud():
                unique_prefix = f"iconnet_v3"
                max_wait = 5.0  # Increased timeout for cloud
            else:
                unique_prefix = f"IconnetApp_{self._session_key}_v3"
                max_wait = 3.0

            # Get password from secrets with fallback
            try:
                password = st.secrets.get(
                    "cookie_password", "iconnet_fallback_key_2025_secure")
            except Exception:
                password = "iconnet_fallback_key_2025_secure"

            # Initialize with unique key and special handling for cloud
            logger.info(f"Initializing cookies with prefix: {unique_prefix}")
            self._cookies = EncryptedCookieManager(
                prefix=unique_prefix,
                password=password
            )

            # Wait for cookies to be ready with timeout
            start_time = time.time()
            check_interval = 0.2 if is_streamlit_cloud() else 0.1

            while (time.time() - start_time) < max_wait:
                if self._cookies.ready():
                    self._ready = True
                    logger.info(
                        f"Cookie manager initialized successfully: {unique_prefix}")
                    return True
                time.sleep(check_interval)

            if is_streamlit_cloud():
                logger.info(
                    "Cookies initialization timeout on cloud - using session state")
            else:
                logger.warning(
                    "Cookies initialization timeout - using session state")

            return False

        except Exception as e:
            if "multiple elements with the same" in str(e).lower():
                logger.warning(
                    "Duplicate cookie manager detected - using session state fallback")
            else:
                logger.warning(
                    f"Cookie initialization failed: {e} - using session state")
            return False

    @property
    def ready(self) -> bool:
        """Check if cookies are ready."""
        if not self._init_attempted:
            self._initialize_cookies()
        return self._ready and self._cookies and self._cookies.ready()

    def save_user_session(self, username: str, email: str, role: str) -> bool:
        """Save user session with dual storage (session state + cookies)."""
        try:
            # Always save to session state (primary storage)
            login_timestamp = time.time()
            session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS

            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False
            st.session_state.login_timestamp = login_timestamp
            st.session_state.session_expiry = session_expiry

            # Try to save to cookies (secondary storage)
            if self.ready:
                try:
                    self._cookies["username"] = username
                    self._cookies["email"] = email
                    self._cookies["role"] = role
                    self._cookies["signout"] = "False"
                    self._cookies["login_timestamp"] = str(login_timestamp)
                    self._cookies["session_expiry"] = str(session_expiry)
                    self._cookies.save()
                    logger.info(
                        f"User {username} saved to both session state and cookies")
                except Exception as e:
                    logger.warning(f"Failed to save to cookies: {e}")
            else:
                logger.info(
                    f"User {username} saved to session state (cookies unavailable)")

            return True

        except Exception as e:
            logger.error(f"Failed to save user session: {e}")
            return False

    def load_user_session(self) -> bool:
        """Load user session from cookies to session state."""
        try:
            # If session state already has valid data, don't override
            current_user = st.session_state.get("username", "")
            current_signout = st.session_state.get("signout", True)
            current_expiry = st.session_state.get("session_expiry", 0)

            # Check if current session is still valid
            if (current_user and not current_signout and
                    current_expiry > time.time()):
                logger.debug(
                    f"Valid session already exists for: {current_user}")
                return True

            # Try to load from cookies if available
            if self.ready:
                try:
                    username = self._cookies.get("username", "") or ""
                    email = self._cookies.get("email", "") or ""
                    role = self._cookies.get("role", "") or ""
                    signout_status = self._cookies.get("signout", "True")

                    # Parse timestamps
                    login_timestamp = None
                    session_expiry = None

                    try:
                        login_timestamp_str = self._cookies.get(
                            "login_timestamp", "")
                        session_expiry_str = self._cookies.get(
                            "session_expiry", "")

                        if login_timestamp_str:
                            login_timestamp = float(login_timestamp_str)
                        if session_expiry_str:
                            session_expiry = float(session_expiry_str)
                    except (ValueError, TypeError):
                        logger.warning("Invalid timestamp in cookies")

                    # Check if session is expired
                    current_time = time.time()
                    if session_expiry and current_time > session_expiry:
                        logger.info(f"Cookie session expired for {username}")
                        self.clear_user_session()
                        return False

                    # Load valid session
                    if username and email and signout_status == "False":
                        st.session_state.username = username
                        st.session_state.useremail = email
                        st.session_state.role = role
                        st.session_state.signout = False

                        if login_timestamp:
                            st.session_state.login_timestamp = login_timestamp
                        if session_expiry:
                            st.session_state.session_expiry = session_expiry

                        logger.info(
                            f"User session restored from cookies: {username}")
                        return True

                except Exception as e:
                    logger.warning(f"Failed to load from cookies: {e}")

            # Set defaults if no valid session found
            if "username" not in st.session_state:
                st.session_state.username = ""
            if "useremail" not in st.session_state:
                st.session_state.useremail = ""
            if "role" not in st.session_state:
                st.session_state.role = ""
            if "signout" not in st.session_state:
                st.session_state.signout = True

            return False

        except Exception as e:
            logger.error(f"Failed to load user session: {e}")
            return False

    def clear_user_session(self) -> bool:
        """Clear user session from both session state and cookies."""
        try:
            # Clear session state
            st.session_state.username = ""
            st.session_state.useremail = ""
            st.session_state.role = ""
            st.session_state.signout = True

            # Clear timestamps
            for key in ['login_timestamp', 'session_expiry', 'user_uid']:
                if key in st.session_state:
                    del st.session_state[key]

            # Clear cookies if available
            if self.ready:
                try:
                    self._cookies["username"] = ""
                    self._cookies["email"] = ""
                    self._cookies["role"] = ""
                    self._cookies["signout"] = "True"
                    self._cookies["login_timestamp"] = ""
                    self._cookies["session_expiry"] = ""
                    self._cookies.save()
                    logger.info(
                        "User session cleared from both session state and cookies")
                except Exception as e:
                    logger.warning(f"Failed to clear cookies: {e}")
            else:
                logger.info("User session cleared from session state")

            return True

        except Exception as e:
            logger.error(f"Failed to clear user session: {e}")
            return False

    def is_user_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        try:
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)
            session_expiry = st.session_state.get("session_expiry", 0)

            # Check if session is valid and not expired
            if username and not signout and session_expiry > time.time():
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to check authentication: {e}")
            return False


def get_cloud_cookie_manager() -> StreamlitCloudCookieManager:
    """Get the singleton cloud cookie manager instance."""
    global _global_cookie_manager

    if _global_cookie_manager is None:
        _global_cookie_manager = StreamlitCloudCookieManager()

    return _global_cookie_manager


# Legacy function compatibility
def save_user_to_cookie(username: str, email: str, role: str) -> bool:
    """Legacy function - save user to cookie."""
    return get_cloud_cookie_manager().save_user_session(username, email, role)


def load_cookie_to_session(session_state) -> bool:
    """Legacy function - load cookie to session."""
    return get_cloud_cookie_manager().load_user_session()


def clear_user_cookie() -> bool:
    """Legacy function - clear user cookie."""
    return get_cloud_cookie_manager().clear_user_session()


# Legacy class for backward compatibility
class CookieManager:
    """Legacy cookie manager for backward compatibility."""

    def __init__(self):
        self._manager = get_cloud_cookie_manager()

    @property
    def ready(self) -> bool:
        return self._manager.ready

    def save_user(self, username: str, email: str, role: str) -> bool:
        return self._manager.save_user_session(username, email, role)

    def clear_user(self) -> bool:
        return self._manager.clear_user_session()

    def load_to_session(self, session_state) -> bool:
        return self._manager.load_user_session()

    def is_user_authenticated(self) -> bool:
        return self._manager.is_user_authenticated()


def get_cookie_manager() -> CookieManager:
    """Get legacy cookie manager instance."""
    return CookieManager()


def check_and_restore_persistent_session():
    """
    Global function to check and restore persistent session.
    This should be called at the very beginning of every page.
    """
    try:
        # Skip if already processing
        if st.session_state.get("_session_restore_in_progress", False):
            return False

        st.session_state._session_restore_in_progress = True

        # Quick check if we have an active session
        username = st.session_state.get("username", "")
        signout = st.session_state.get("signout", True)
        session_expiry = st.session_state.get("session_expiry", 0)

        # If we have a valid session, no need to restore
        if username and not signout and session_expiry > time.time():
            st.session_state._session_restore_in_progress = False
            return True

        # Look for persistent session data
        session_restored = False

        # Strategy 1: Look for encoded session data
        for key in list(st.session_state.keys()):
            if any(term in key for term in ['encoded_session', 'iconnet_session', 'backup_session']):
                try:
                    encoded_data = st.session_state[key]
                    if isinstance(encoded_data, str):
                        session_data = json.loads(encoded_data)

                        # Validate session
                        if (session_data.get('session_expiry', 0) > time.time() and
                                session_data.get('username')):

                            # Restore session variables
                            st.session_state.username = session_data.get(
                                'username', '')
                            st.session_state.useremail = session_data.get(
                                'email', '')
                            st.session_state.role = session_data.get(
                                'role', '')
                            st.session_state.signout = session_data.get(
                                'signout', True)
                            st.session_state.login_timestamp = session_data.get(
                                'login_timestamp', time.time())
                            st.session_state.session_expiry = session_data.get(
                                'session_expiry', 0)

                            logger.info(
                                f"🟢 Persistent session restored for: {session_data.get('username')}")
                            session_restored = True
                            break
                        else:
                            # Clean up expired session
                            try:
                                del st.session_state[key]
                            except:
                                pass
                except Exception as e:
                    logger.debug(f"Failed to parse session from {key}: {e}")

        # Strategy 2: Look for persistent auth records
        if not session_restored:
            for key in list(st.session_state.keys()):
                if key.startswith('persistent_auth_'):
                    try:
                        auth_data = st.session_state[key]
                        if auth_data.get('expiry', 0) > time.time():
                            session_str = auth_data.get('session', '')
                            if session_str:
                                session_data = json.loads(session_str)

                                # Restore session
                                st.session_state.username = session_data.get(
                                    'username', '')
                                st.session_state.useremail = session_data.get(
                                    'email', '')
                                st.session_state.role = session_data.get(
                                    'role', '')
                                st.session_state.signout = session_data.get(
                                    'signout', True)
                                st.session_state.login_timestamp = session_data.get(
                                    'login_timestamp', time.time())
                                st.session_state.session_expiry = session_data.get(
                                    'session_expiry', 0)

                                logger.info(
                                    f"🟢 Session restored from persistent auth: {session_data.get('username')}")
                                session_restored = True
                                break
                        else:
                            # Clean up expired auth
                            try:
                                del st.session_state[key]
                            except:
                                pass
                    except Exception as e:
                        logger.debug(
                            f"Failed to parse persistent auth {key}: {e}")

        st.session_state._session_restore_in_progress = False
        return session_restored

    except Exception as e:
        logger.error(f"Persistent session check failed: {e}")
        st.session_state._session_restore_in_progress = False
        return False

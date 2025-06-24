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
        """Initialize cookies with enhanced cloud compatibility and timing."""
        if self._init_attempted:
            return self._ready

        self._init_attempted = True

        try:
            # Skip if cookies library not available
            if not COOKIES_AVAILABLE or EncryptedCookieManager is None:
                logger.warning(
                    "streamlit-cookies-manager not available, using session state only")
                return False

            # Check Streamlit context with enhanced detection
            try:
                import streamlit.runtime.scriptrunner as sr
                ctx = sr.get_script_run_ctx()
                if ctx is None:
                    logger.debug(
                        "Not in Streamlit context - using session state only")
                    return False
            except (ImportError, AttributeError):
                # Fallback context check
                try:
                    if not hasattr(st, 'session_state'):
                        logger.debug("Streamlit session_state not available")
                        return False
                except Exception:
                    return False

            # Enhanced cloud detection and configuration
            is_cloud = is_streamlit_cloud()

            if is_cloud:
                # Cloud-optimized settings
                unique_prefix = "iconnet_cloud_v4"
                max_wait = 8.0  # Increased timeout for cloud
                check_interval = 0.3
                logger.info("🌐 Detected Streamlit Cloud environment")
            else:
                # Local development settings
                unique_prefix = f"iconnet_local_{self._session_key}_v4"
                max_wait = 4.0
                check_interval = 0.1
                logger.info("💻 Detected local development environment")

            # Enhanced password handling with validation
            try:
                password = st.secrets.get("cookie_password")
                if not password:
                    raise KeyError("cookie_password not found in secrets")

                # Validate password strength
                if len(password) < 16:
                    logger.warning(
                        "⚠️ Cookie password should be at least 16 characters")

                logger.info("✅ Cookie password loaded from secrets")
            except Exception as e:
                # Stronger fallback password
                password = "iconnet_secure_fallback_2025_v4_minimum_32chars"
                logger.warning(f"⚠️ Using fallback cookie password: {e}")
                logger.warning(
                    "🔧 Please set 'cookie_password' in Streamlit secrets")

            # Pre-initialization delay for cloud stability
            if is_cloud:
                time.sleep(0.5)  # Give cloud environment time to stabilize

            # Initialize with retry mechanism
            initialization_attempts = 2 if is_cloud else 1

            for attempt in range(initialization_attempts):
                try:
                    logger.info(
                        f"🔄 Initializing cookies (attempt {attempt + 1}/{initialization_attempts})")
                    logger.info(f"📝 Using prefix: {unique_prefix}")

                    self._cookies = EncryptedCookieManager(
                        prefix=unique_prefix,
                        password=password
                    )

                    # Enhanced readiness check with exponential backoff
                    start_time = time.time()
                    current_interval = check_interval
                    max_interval = 1.0

                    while (time.time() - start_time) < max_wait:
                        try:
                            if self._cookies.ready():
                                self._ready = True
                                elapsed = time.time() - start_time
                                logger.info(
                                    f"✅ Cookie manager ready in {elapsed:.2f}s: {unique_prefix}")

                                # Test basic functionality
                                test_key = f"test_{int(time.time())}"
                                self._cookies[test_key] = "test_value"
                                if self._cookies.get(test_key) == "test_value":
                                    logger.info(
                                        "✅ Cookie functionality verified")
                                    # Clean up test
                                    del self._cookies[test_key]
                                else:
                                    logger.warning(
                                        "⚠️ Cookie read/write test failed")

                                return True
                        except Exception as ready_error:
                            logger.debug(
                                f"Cookie ready check failed: {ready_error}")

                        time.sleep(current_interval)
                        # Exponential backoff (but cap at max_interval)
                        current_interval = min(
                            current_interval * 1.2, max_interval)

                    # If we reach here, this attempt timed out
                    logger.warning(
                        f"⏰ Attempt {attempt + 1} timed out after {max_wait}s")

                    if attempt < initialization_attempts - 1:
                        # Wait before retry
                        time.sleep(1.0)
                        continue

                except Exception as init_error:
                    logger.warning(
                        f"❌ Initialization attempt {attempt + 1} failed: {init_error}")
                    if attempt < initialization_attempts - 1:
                        time.sleep(1.0)
                        continue

            # All attempts failed
            if is_cloud:
                logger.info(
                    "☁️ Cloud cookies initialization failed - using session state fallback")
            else:
                logger.warning(
                    "💻 Local cookies initialization failed - using session state fallback")

            return False

        except Exception as e:
            error_msg = str(e).lower()
            if "multiple elements with the same" in error_msg:
                logger.warning(
                    "🔄 Duplicate cookie manager detected - using session state fallback")
            elif "streamlit" in error_msg and "context" in error_msg:
                logger.debug(
                    "🔄 Streamlit context issue - using session state fallback")
            else:
                logger.warning(
                    f"❌ Cookie initialization failed: {e} - using session state fallback")
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


def initialize_cookies_early() -> bool:
    """
    Initialize cookies as early as possible in the Streamlit app lifecycle.
    This should be called at the very beginning of main pages.

    Returns:
        bool: True if cookies are available, False if using session state only
    """
    try:
        # Get or create the global cookie manager
        cookie_manager = get_cloud_cookie_manager()

        # Force initialization if not attempted yet
        if not cookie_manager._init_attempted:
            logger.info("🚀 Performing early cookie initialization...")
            success = cookie_manager._initialize_cookies()

            if success:
                logger.info("✅ Early cookie initialization successful")
                return True
            else:
                logger.info(
                    "ℹ️ Cookies not available - using session state mode")
                return False

        # Return current status
        return cookie_manager.ready

    except Exception as e:
        logger.error(f"❌ Early cookie initialization failed: {e}")
        return False


def ensure_cookie_compatibility() -> Dict[str, Any]:
    """
    Ensure cookie compatibility and return status information.
    Useful for debugging and user feedback.

    Returns:
        Dict with detailed status information
    """
    try:
        cookie_manager = get_cloud_cookie_manager()

        status = {
            "library_available": COOKIES_AVAILABLE,
            "manager_ready": cookie_manager.ready if cookie_manager else False,
            "cloud_detected": is_streamlit_cloud(),
            "session_timeout_hours": SESSION_TIMEOUT_HOURS,
            "init_attempted": cookie_manager._init_attempted if cookie_manager else False,
            "current_user": st.session_state.get("username", ""),
            "session_mode": "cookies" if (cookie_manager and cookie_manager.ready) else "session_state"
        }

        # Add recommendations
        if not status["library_available"]:
            status["recommendation"] = "Install streamlit-cookies-manager: pip install streamlit-cookies-manager"
        elif not status["manager_ready"]:
            status["recommendation"] = "Check cookie_password in Streamlit secrets and network connectivity"
        else:
            status["recommendation"] = "Cookie system working properly"

        return status

    except Exception as e:
        return {
            "error": str(e),
            "library_available": COOKIES_AVAILABLE,
            "session_mode": "session_state",
            "recommendation": "Check application logs for detailed error information"
        }


def check_service_conflicts() -> Dict[str, Any]:
    """
    Check for potential conflicts dengan services lain yang bisa 
    mempengaruhi cookie manager timing.
    """
    conflicts = {
        "detected_conflicts": [],
        "performance_impact": "low",
        "recommendations": []
    }

    try:
        # Check 1: Multiple Streamlit components yang bisa conflict
        component_checks = [
            ("streamlit-option-menu", "Menu component loading"),
            ("streamlit-folium", "Map component loading"),
            ("extra-streamlit-components", "Extra UI components"),
            ("plotly", "Heavy plotting library"),
        ]

        for package, description in component_checks:
            try:
                __import__(package.replace("-", "_"))
                # Check if component sedang initialize bersamaan
                if hasattr(st.session_state, f"_{package}_initializing"):
                    conflicts["detected_conflicts"].append({
                        "component": package,
                        "issue": "Concurrent initialization detected",
                        "impact": "medium"
                    })
            except ImportError:
                pass

        # Check 2: Database connections yang bisa block
        db_services = ["firebase_admin", "psycopg2", "sqlalchemy"]
        for service in db_services:
            try:
                __import__(service)
                # Check if ada connection yang sedang dibuat
                if hasattr(st.session_state, f"_{service}_connecting"):
                    conflicts["detected_conflicts"].append({
                        "service": service,
                        "issue": "Database connection in progress",
                        "impact": "high"
                    })
            except ImportError:
                pass

        # Check 3: AI Services yang resource-intensive
        ai_services = ["langchain", "google.generativeai", "openai"]
        for service in ai_services:
            try:
                if "." in service:
                    module_parts = service.split(".")
                    __import__(module_parts[0])
                else:
                    __import__(service)

                # Check if model loading sedang berlangsung
                if hasattr(st.session_state, f"_{service.replace('.', '_')}_loading"):
                    conflicts["detected_conflicts"].append({
                        "service": service,
                        "issue": "AI model loading concurrent with cookies",
                        "impact": "high"
                    })
            except ImportError:
                pass

        # Check 4: Session state pollution
        large_objects = []
        for key, value in st.session_state.items():
            try:
                # Rough size estimation
                size = len(str(value))
                if size > 10000:  # Large objects > 10KB
                    large_objects.append((key, size))
            except Exception:
                pass

        if large_objects:
            conflicts["detected_conflicts"].append({
                "issue": "Large objects in session state",
                "details": large_objects[:5],  # Top 5 largest
                "impact": "medium"
            })

        # Performance impact assessment
        total_conflicts = len(conflicts["detected_conflicts"])
        high_impact = sum(
            1 for c in conflicts["detected_conflicts"] if c.get("impact") == "high")

        if high_impact > 0:
            conflicts["performance_impact"] = "high"
        elif total_conflicts > 2:
            conflicts["performance_impact"] = "medium"
        else:
            conflicts["performance_impact"] = "low"

        # Generate recommendations
        if conflicts["performance_impact"] in ["high", "medium"]:
            conflicts["recommendations"].extend([
                "Initialize cookies sebelum services lain",
                "Gunakan lazy loading untuk heavy components",
                "Implement service initialization queue",
                "Clear large objects dari session state",
                "Add delays between service initializations"
            ])

        return conflicts

    except Exception as e:
        logger.error(f"Conflict detection failed: {e}")
        return {
            "error": str(e),
            "detected_conflicts": [],
            "performance_impact": "unknown"
        }


def implement_service_isolation():
    """
    Implement service isolation untuk menghindari conflicts.
    """
    # Strategy 1: Initialize cookies FIRST, before everything else
    if not hasattr(st.session_state, "_cookies_initialized"):
        logger.info("🏁 Initializing cookies with service isolation...")

        # Mark sebagai sedang initialize
        st.session_state._cookies_initializing = True

        try:
            # Initialize cookies dalam isolated environment
            cookie_success = initialize_cookies_early()
            st.session_state._cookies_initialized = True
            st.session_state._cookies_available = cookie_success

            logger.info(
                f"✅ Cookies isolated initialization: {'success' if cookie_success else 'fallback'}")

        except Exception as e:
            logger.error(f"❌ Isolated cookie initialization failed: {e}")
            st.session_state._cookies_initialized = True
            st.session_state._cookies_available = False
        finally:
            # Clean up initialization flag
            if hasattr(st.session_state, "_cookies_initializing"):
                del st.session_state._cookies_initializing

    # Strategy 2: Delay other service initialization
    if st.session_state.get("_cookies_initialized") and not hasattr(st.session_state, "_services_initialized"):
        logger.info("🔄 Starting other services after cookies...")

        # Small delay untuk memastikan cookies sudah stabil
        time.sleep(0.2)

        try:
            # Initialize services dengan controlled order
            service_order = [
                ("database", _initialize_database_service),
                ("firebase", _initialize_firebase_service),
                ("ai_services", _initialize_ai_services),
                ("ui_components", _initialize_ui_components)
            ]

            for service_name, init_func in service_order:
                try:
                    logger.info(f"🔧 Initializing {service_name}...")
                    init_func()
                    # Small delay between services
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(
                        f"❌ {service_name} initialization failed: {e}")
                    # Continue dengan service lain
                    continue

            st.session_state._services_initialized = True
            logger.info("✅ All services initialized with isolation")

        except Exception as e:
            logger.error(f"❌ Service isolation failed: {e}")


def _initialize_database_service():
    """Initialize database services dengan error handling."""
    try:
        if not hasattr(st.session_state, "db"):
            from core.utils.database import connect_db
            st.session_state.db = connect_db()
    except Exception as e:
        logger.warning(f"Database service init failed: {e}")


def _initialize_firebase_service():
    """Initialize Firebase services dengan error handling."""
    try:
        if not hasattr(st.session_state, "fs"):
            from core.utils.firebase_config import get_firebase_app
            fs, auth, config = get_firebase_app()
            st.session_state.fs = fs
            st.session_state.auth = auth
            st.session_state.fs_config = config
    except Exception as e:
        logger.warning(f"Firebase service init failed: {e}")


def _initialize_ai_services():
    """Initialize AI services dengan lazy loading."""
    try:
        # Mark sebagai available tapi jangan load heavy models yet
        st.session_state._ai_services_available = True
        # Actual model loading akan dilakukan on-demand
    except Exception as e:
        logger.warning(f"AI services init failed: {e}")


def _initialize_ui_components():
    """Initialize UI components yang non-critical."""
    try:
        # Load CSS dan static assets
        from core.utils.load_css import load_custom_css
        load_custom_css()
    except Exception as e:
        logger.warning(f"UI components init failed: {e}")

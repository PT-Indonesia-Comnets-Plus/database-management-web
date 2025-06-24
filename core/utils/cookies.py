"""
🔧 STREAMLIT CLOUD PERSISTENT LOGIN - PRODUCTION READY
====================================================

Optimized cookie management utilities for user session persistence.
Designed for maximum compatibility with both local development and Streamlit Cloud.

Features:
- Multiple fallback methods for secrets detection
- Enhanced Streamlit Cloud compatibility 
- Robust session persistence across page refreshes
- Performance optimization with timeout handling
- Comprehensive error handling and logging
- Zero deprecated API usage

"""

import streamlit as st
from typing import Optional, Dict, Any
import time
import logging
import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta

# Cookie manager import with error handling
try:
    from streamlit_cookies_manager import EncryptedCookieManager
    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False
    EncryptedCookieManager = None

logger = logging.getLogger(__name__)

# Configuration constants
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600
COOKIE_EXPIRY_DAYS = 7
COOKIE_MAX_INIT_TIME = 12.0  # Maximum time to wait for cookie initialization


class StreamlitCloudDetector:
    """Enhanced Streamlit Cloud detection utility."""

    @staticmethod
    def is_streamlit_cloud() -> bool:
        """Detect if running on Streamlit Cloud with multiple indicators."""
        try:
            # Primary cloud indicators
            cloud_indicators = [
                os.getenv("STREAMLIT_SHARING_MODE") == "1",
                os.getenv("STREAMLIT_CLOUD_MODE") == "1",
                "streamlit.app" in os.getenv("HOSTNAME", "").lower(),
                "streamlit.app" in os.getenv("SERVER_NAME", "").lower(),
                "/mount/src/" in os.getcwd(),
                os.path.exists("/.dockerenv"),
                os.getenv("HOME", "").startswith("/home/appuser"),
            ]

            # Server configuration indicators
            try:
                server_address = str(st.get_option("server.address") or "")
                if "0.0.0.0" in server_address:
                    cloud_indicators.append(True)
            except Exception:
                pass

            # Port-based detection
            try:
                port = st.get_option("server.port")
                if port == 8501:  # Default cloud port
                    cloud_indicators.append(True)
            except Exception:
                pass

            result = any(cloud_indicators)
            logger.info(f"🌐 Cloud detection result: {result}")
            return result

        except Exception as e:
            logger.warning(f"Cloud detection error: {e}")
            return False


class SecretsManager:
    """Enhanced secrets management with multiple fallback methods."""

    @staticmethod
    def get_cookie_password() -> Optional[str]:
        """Get cookie password using multiple fallback methods."""
        password_methods = [
            # Method 1: Direct flat access (recommended format)
            ("Direct flat access", lambda: st.secrets.get("cookie_password")),

            # Method 2: Nested format support
            ("Nested format", lambda: st.secrets.get("cookie", {}).get("password")
             if isinstance(st.secrets.get("cookie"), dict) else None),

            # Method 3: Alternative naming conventions
            ("Alternative naming", lambda: st.secrets.get("cookies_password")),
            ("Session password", lambda: st.secrets.get("session_password")),
            ("Auth password", lambda: st.secrets.get("auth_password")),

            # Method 4: Direct key access (for TOML sections)
            ("Direct key", lambda: getattr(st.secrets, "cookie_password", None)),

            # Method 5: Manual TOML parsing fallback
            ("Manual TOML", SecretsManager._parse_toml_manually),
        ]

        for method_name, get_password in password_methods:
            try:
                password = get_password()
                if password and isinstance(password, str) and len(password.strip()) > 0:
                    logger.info(
                        f"✅ Cookie password found using: {method_name}")
                    return password.strip()
            except Exception as e:
                logger.debug(f"❌ {method_name} failed: {e}")
                continue

        # If all methods fail, log available keys for debugging
        SecretsManager._log_available_secrets()

        # Generate a secure fallback password for Streamlit Cloud
        fallback_password = SecretsManager._generate_fallback_password()
        logger.warning(
            f"🔧 Using generated fallback password for session management")
        return fallback_password

    @staticmethod
    def _parse_toml_manually() -> Optional[str]:
        """Manual TOML parsing as absolute fallback."""
        try:
            secrets_path = ".streamlit/secrets.toml"
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r') as f:
                    content = f.read()
                    # Look for cookie_password in various formats
                    import re
                    patterns = [
                        r'cookie_password\s*=\s*["\']([^"\']+)["\']',
                        r'password\s*=\s*["\']([^"\']+)["\']',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, content)
                        if match:
                            return match.group(1)
        except Exception as e:
            logger.debug(f"Manual TOML parsing failed: {e}")
        return None

    @staticmethod
    def _generate_fallback_password() -> str:
        """Generate a secure fallback password for Streamlit Cloud."""
        try:
            import hashlib
            import uuid

            # Use a combination of app-specific and deployment-specific identifiers
            cloud_indicators = [
                os.getenv("STREAMLIT_SHARING_MODE", ""),
                os.getenv("HOSTNAME", ""),
                str(uuid.getnode()),  # MAC address
                "iconnet_fallback_2024"
            ]

            combined = "_".join(str(x) for x in cloud_indicators if x)
            return hashlib.sha256(combined.encode()).hexdigest()[:32]

        except Exception as e:
            logger.warning(f"Fallback password generation failed: {e}")
            return "iconnet_default_fallback_key_2024"

    @staticmethod
    def _log_available_secrets():
        """Log available secret keys for debugging."""
        try:
            available_keys = []
            for key in dir(st.secrets):
                if not key.startswith('_'):
                    available_keys.append(key)

            logger.error(f"❌ Cookie password not found in any format")
            logger.error(f"Available secrets keys: {available_keys}")

            # Also check if secrets is accessible at all
            logger.info(f"📋 Secrets object type: {type(st.secrets)}")

        except Exception as e:
            logger.error(f"Failed to log available secrets: {e}")


class OptimizedCookieManager:
    """Production-ready cookie manager optimized for Streamlit Cloud."""

    def __init__(self):
        """Initialize with optimized settings."""
        self._manager = None
        self._ready = False
        self._init_attempted = False
        self._session_key = f"iconnet_session_{self._generate_session_id()}"
        self._is_cloud = StreamlitCloudDetector.is_streamlit_cloud()

    def _generate_session_id(self) -> str:
        """Generate a unique session identifier."""
        try:
            # Create session ID based on timestamp and random component
            timestamp = str(int(time.time() / 3600))  # Changes every hour
            random_part = str(uuid.uuid4())[:8]
            session_data = f"{timestamp}_{random_part}"
            return hashlib.md5(session_data.encode()).hexdigest()[:12]
        except Exception:
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

    def initialize(self) -> bool:
        """Initialize cookie manager with enhanced error handling."""
        if self._init_attempted:
            return self._ready

        self._init_attempted = True

        try:
            # Check if cookies are available
            if not COOKIES_AVAILABLE:
                logger.warning("📦 streamlit-cookies-manager not available")
                return False

            # Check Streamlit context
            if not self._check_streamlit_context():
                logger.info("🚫 Not in valid Streamlit context")
                return False

            # Get cookie password
            password = SecretsManager.get_cookie_password()
            if not password:
                logger.error("🔑 Cookie password not found in secrets")
                return False

            # Initialize cookie manager with optimized settings
            config = self._get_optimized_config()

            logger.info(
                f"🍪 Initializing cookies for {'cloud' if self._is_cloud else 'local'} environment")

            self._manager = EncryptedCookieManager(
                prefix=config['prefix'],
                password=password,
                expiry_days=config['expiry_days']
            )

            # Wait for initialization with timeout
            start_time = time.time()
            max_wait = config['max_wait_time']

            while not self._manager.ready():
                if time.time() - start_time > max_wait:
                    logger.warning(
                        f"⏰ Cookie initialization timeout after {max_wait}s")
                    return False
                time.sleep(0.2)

            self._ready = True
            logger.info("✅ Cookie manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Cookie initialization failed: {e}")
            return False

    def _check_streamlit_context(self) -> bool:
        """Check if we're in a valid Streamlit context."""
        try:
            # Method 1: Check session state
            if not hasattr(st, 'session_state'):
                return False

            # Method 2: Try to access session state
            _ = st.session_state            # Method 3: Check script run context
            try:
                import streamlit.runtime.scriptrunner as sr
                ctx = sr.get_script_run_ctx()
                return ctx is not None
            except (ImportError, AttributeError):
                # Fallback for older versions
                return True

        except Exception:
            return False

    def _get_optimized_config(self) -> Dict[str, Any]:
        """Get optimized configuration based on environment."""
        if self._is_cloud:
            return {
                'prefix': f"iconnet_cloud_v6_{self._session_key}",
                'expiry_days': COOKIE_EXPIRY_DAYS,
                'max_wait_time': 20.0,  # Longer timeout for cloud
            }
        else:
            return {
                'prefix': f"iconnet_local_v6_{self._session_key}",
                'expiry_days': COOKIE_EXPIRY_DAYS,
                'max_wait_time': 8.0,   # Shorter timeout for local
            }

    def save_user_session(self, user_data: Dict[str, Any]) -> bool:
        """Save user session to cookies with fallback to session state."""
        try:
            # Always save to session state as primary storage
            session_data = {
                **user_data,
                'saved_at': time.time(),
                'expires_at': time.time() + SESSION_TIMEOUT_SECONDS
            }
            st.session_state['user_session'] = session_data

            # Try to save to cookies as secondary storage
            if self._ready and self._manager:
                try:
                    self._manager['user_session'] = json.dumps(session_data)
                    self._manager.save()
                    logger.info(
                        "✅ User session saved to cookies and session state")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Cookie save failed, using session state only: {e}")
            else:
                logger.info("📝 User session saved to session state only")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to save user session: {e}")
            return False

    def load_user_session(self) -> Optional[Dict[str, Any]]:
        """Load user session from cookies or session state."""
        try:
            # Try session state first (fastest)
            session_data = self._load_from_session_state()
            if session_data and self._is_session_valid(session_data):
                logger.debug("📱 Loaded valid session from session state")
                return session_data

            # Try cookies as fallback
            if self._ready and self._manager:
                cookie_data = self._load_from_cookies()
                if cookie_data and self._is_session_valid(cookie_data):
                    # Restore to session state
                    st.session_state['user_session'] = cookie_data
                    logger.info(
                        "🍪 Restored session from cookies to session state")
                    return cookie_data

            logger.debug("🚫 No valid session found")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to load user session: {e}")
            return None

    def _load_from_session_state(self) -> Optional[Dict[str, Any]]:
        """Load session data from Streamlit session state."""
        try:
            return st.session_state.get('user_session')
        except Exception:
            return None

    def _load_from_cookies(self) -> Optional[Dict[str, Any]]:
        """Load session data from cookies."""
        try:
            if not self._ready or not self._manager:
                return None

            session_json = self._manager.get('user_session')
            if session_json:
                return json.loads(session_json)
            return None

        except Exception as e:
            logger.debug(f"Cookie load failed: {e}")
            return None

    def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session data is valid and not expired."""
        try:
            if not isinstance(session_data, dict):
                return False

            # Check required fields
            required_fields = ['user_id', 'email', 'saved_at']
            if not all(field in session_data for field in required_fields):
                return False

            # Check expiration
            expires_at = session_data.get('expires_at', 0)
            if time.time() > expires_at:
                logger.debug("🕐 Session expired")
                return False

            return True

        except Exception:
            return False

    def clear_session(self) -> bool:
        """Clear user session from both cookies and session state."""
        try:
            # Clear session state
            if 'user_session' in st.session_state:
                del st.session_state['user_session']

            # Clear cookies
            if self._ready and self._manager:
                try:
                    if 'user_session' in self._manager:
                        del self._manager['user_session']
                    self._manager.save()
                    logger.info(
                        "✅ Session cleared from cookies and session state")
                except Exception as e:
                    logger.warning(f"⚠️ Cookie clear failed: {e}")
            else:
                logger.info("📝 Session cleared from session state")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to clear session: {e}")
            return False

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about cookie manager state."""
        return {
            'cookies_available': COOKIES_AVAILABLE,
            'manager_ready': self._ready,
            'init_attempted': self._init_attempted,
            'is_cloud': self._is_cloud,
            'session_key': self._session_key,
            'has_session_state': 'user_session' in st.session_state if hasattr(st, 'session_state') else False,
            'cookie_password_available': SecretsManager.get_cookie_password() is not None,
        }


# Global instance
_global_cookie_manager = None


def get_cookie_manager() -> OptimizedCookieManager:
    """Get the global cookie manager instance."""
    global _global_cookie_manager

    if _global_cookie_manager is None:
        _global_cookie_manager = OptimizedCookieManager()

        # Try to initialize if not already done
        if not _global_cookie_manager._init_attempted:
            _global_cookie_manager.initialize()

    return _global_cookie_manager


def save_user_to_cookie(user_data: Dict[str, Any]) -> bool:
    """Save user session data to cookies and session state."""
    manager = get_cookie_manager()
    return manager.save_user_session(user_data)


def load_user_from_cookie() -> Optional[Dict[str, Any]]:
    """Load user session data from cookies or session state."""
    manager = get_cookie_manager()
    return manager.load_user_session()


def clear_user_cookie() -> bool:
    """Clear user session from cookies and session state."""
    manager = get_cookie_manager()
    return manager.clear_session()


def get_debug_info() -> Dict[str, Any]:
    """Get comprehensive debug information."""
    manager = get_cookie_manager()
    return manager.get_debug_info()


# Backward compatibility aliases
get_cloud_cookie_manager = get_cookie_manager

# Alias function to match existing usage


def is_streamlit_cloud() -> bool:
    """Alias for StreamlitCloudDetector.is_streamlit_cloud()."""
    return StreamlitCloudDetector.is_streamlit_cloud()

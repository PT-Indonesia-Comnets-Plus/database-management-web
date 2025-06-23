"""
Streamlit Cloud optimized cookie implementation with robust session persistence.
This module provides a reliable cookie-based session management specifically designed for Streamlit Cloud.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import time
import logging
import hashlib
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Session configuration
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600


class StreamlitCloudSessionManager:
    """
    Advanced session manager for Streamlit Cloud using multiple persistence strategies.
    Uses localStorage, sessionStorage, and cookies for maximum reliability.
    """

    def __init__(self):
        """Initialize the session manager."""
        self._session_id = self._generate_session_id()
        self._storage_prefix = f"iconnet_app_{self._session_id}"
        self._initialized = False

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        try:
            # Try to get existing session ID from streamlit session
            if hasattr(st.session_state, '_iconnet_session_id'):
                return st.session_state._iconnet_session_id

            # Generate new session ID
            session_id = str(uuid.uuid4())[:8]
            st.session_state._iconnet_session_id = session_id
            return session_id
        except Exception:
            return str(time.time())[-8:]

    def _create_js_storage_component(self, action: str, data: Dict = None) -> str:
        """Create JavaScript component for browser storage operations."""
        data_json = json.dumps(data or {})
        prefix = self._storage_prefix

        js_code = f"""
        <script>
        (function() {{
            const prefix = "{prefix}";
            const action = "{action}";
            const data = {data_json};
            
            function setStorageItem(key, value) {{
                try {{
                    // Store in localStorage (persistent)
                    localStorage.setItem(prefix + "_" + key, JSON.stringify(value));
                    // Store in sessionStorage (backup)
                    sessionStorage.setItem(prefix + "_" + key, JSON.stringify(value));
                    return true;
                }} catch (e) {{
                    console.warn("Storage failed:", e);
                    return false;
                }}
            }}
            
            function getStorageItem(key) {{
                try {{
                    // Try localStorage first
                    let item = localStorage.getItem(prefix + "_" + key);
                    if (item) return JSON.parse(item);
                    
                    // Fallback to sessionStorage
                    item = sessionStorage.getItem(prefix + "_" + key);
                    if (item) return JSON.parse(item);
                    
                    return null;
                }} catch (e) {{
                    console.warn("Storage read failed:", e);
                    return null;
                }}
            }}
            
            function clearStorage() {{
                try {{
                    // Clear all keys with our prefix
                    Object.keys(localStorage).forEach(key => {{
                        if (key.startsWith(prefix)) {{
                            localStorage.removeItem(key);
                        }}
                    }});
                    Object.keys(sessionStorage).forEach(key => {{
                        if (key.startsWith(prefix)) {{
                            sessionStorage.removeItem(key);
                        }}
                    }});
                    return true;
                }} catch (e) {{
                    console.warn("Storage clear failed:", e);
                    return false;
                }}
            }}
            
            function setCookie(name, value, days = 7) {{
                try {{
                    const expires = new Date();
                    expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
                    document.cookie = name + "=" + encodeURIComponent(JSON.stringify(value)) + 
                                    ";expires=" + expires.toUTCString() + 
                                    ";path=/;SameSite=Lax;Secure";
                    return true;
                }} catch (e) {{
                    console.warn("Cookie set failed:", e);
                    return false;
                }}
            }}
            
            function getCookie(name) {{
                try {{
                    const nameEQ = name + "=";
                    const ca = document.cookie.split(';');
                    for (let i = 0; i < ca.length; i++) {{
                        let c = ca[i];
                        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                        if (c.indexOf(nameEQ) === 0) {{
                            return JSON.parse(decodeURIComponent(c.substring(nameEQ.length, c.length)));
                        }}
                    }}
                    return null;
                }} catch (e) {{
                    console.warn("Cookie read failed:", e);
                    return null;
                }}
            }}
            
            function clearCookies() {{
                try {{
                    const cookies = document.cookie.split(";");
                    for (let cookie of cookies) {{
                        const eqPos = cookie.indexOf("=");
                        const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
                        if (name.startsWith(prefix)) {{
                            document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
                        }}
                    }}
                    return true;
                }} catch (e) {{
                    console.warn("Cookie clear failed:", e);
                    return false;
                }}
            }}
            
            // Execute action
            let result = {{}};
            
            if (action === "save") {{
                const success = setStorageItem("session", data) && setCookie(prefix + "_session", data, 7);
                result = {{success: success, message: success ? "Session saved" : "Save failed"}};
            }} else if (action === "load") {{
                let sessionData = getStorageItem("session");
                if (!sessionData) {{
                    sessionData = getCookie(prefix + "_session");
                }}
                result = {{data: sessionData, success: sessionData !== null}};
            }} else if (action === "clear") {{
                const success = clearStorage() && clearCookies();
                result = {{success: success, message: success ? "Session cleared" : "Clear failed"}};
            }} else if (action === "check") {{
                const hasLocalStorage = typeof(Storage) !== "undefined";
                const hasCookies = navigator.cookieEnabled;
                result = {{
                    localStorage: hasLocalStorage,
                    cookies: hasCookies,
                    supported: hasLocalStorage || hasCookies
                }};
            }}
            
            // Send result back to Streamlit
            window.parent.postMessage({{
                type: "streamlit:componentValue",
                value: result
            }}, "*");
        }})();
        </script>
        """

        return js_code

    def _execute_js_action(self, action: str, data: Dict = None) -> Optional[Dict]:
        """Execute JavaScript action and return result."""
        try:
            js_code = self._create_js_storage_component(action, data)
            result = components.html(
                js_code, height=0, key=f"{self._storage_prefix}_{action}_{time.time()}")
            return result
        except Exception as e:
            logger.error(f"JavaScript execution failed: {e}")
            return None

    def save_user_session(self, username: str, email: str, role: str) -> bool:
        """Save user session to persistent storage."""
        try:
            # Always save to Streamlit session state first
            login_timestamp = time.time()
            session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS

            session_data = {
                "username": username,
                "email": email,
                "role": role,
                "login_timestamp": login_timestamp,
                "session_expiry": session_expiry,
                "signout": False,
                "version": "2.0"
            }

            # Save to session state
            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False
            st.session_state.login_timestamp = login_timestamp
            st.session_state.session_expiry = session_expiry

            # Save to browser storage
            result = self._execute_js_action("save", session_data)

            if result and result.get("success"):
                logger.info(f"User session saved successfully for: {username}")
                return True
            else:
                logger.warning(
                    f"Browser storage save failed for: {username}, using session state only")
                return True  # Still return True as session state worked

        except Exception as e:
            logger.error(f"Failed to save user session: {e}")
            return False

    def load_user_session(self) -> bool:
        """Load user session from persistent storage."""
        try:
            # Check if we already have a valid session in session state
            current_user = st.session_state.get("username", "")
            current_signout = st.session_state.get("signout", True)
            current_expiry = st.session_state.get("session_expiry", 0)

            # If current session is valid and not expired, use it
            if (current_user and not current_signout and
                    current_expiry > time.time()):
                logger.debug(
                    f"Valid session already exists for: {current_user}")
                return True

            # Try to load from browser storage
            result = self._execute_js_action("load")

            if result and result.get("success") and result.get("data"):
                session_data = result["data"]

                # Validate session data
                required_fields = ["username",
                                   "email", "role", "session_expiry"]
                if not all(field in session_data for field in required_fields):
                    logger.warning("Invalid session data structure")
                    return self._set_default_session()

                # Check if session is expired
                session_expiry = session_data.get("session_expiry", 0)
                if time.time() > session_expiry:
                    logger.info("Stored session has expired")
                    self.clear_user_session()
                    return self._set_default_session()

                # Load valid session
                st.session_state.username = session_data["username"]
                st.session_state.useremail = session_data["email"]
                st.session_state.role = session_data["role"]
                st.session_state.signout = session_data.get("signout", False)
                st.session_state.login_timestamp = session_data.get(
                    "login_timestamp", time.time())
                st.session_state.session_expiry = session_expiry

                logger.info(
                    f"User session restored from storage: {session_data['username']}")
                return True

            # No valid session found, set defaults
            return self._set_default_session()

        except Exception as e:
            logger.error(f"Failed to load user session: {e}")
            return self._set_default_session()

    def clear_user_session(self) -> bool:
        """Clear user session from all storage."""
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

            # Clear browser storage
            result = self._execute_js_action("clear")

            if result and result.get("success"):
                logger.info("User session cleared from all storage")
            else:
                logger.warning(
                    "Browser storage clear may have failed, session state cleared")

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

    def _set_default_session(self) -> bool:
        """Set default session state values."""
        if "username" not in st.session_state:
            st.session_state.username = ""
        if "useremail" not in st.session_state:
            st.session_state.useremail = ""
        if "role" not in st.session_state:
            st.session_state.role = ""
        if "signout" not in st.session_state:
            st.session_state.signout = True
        return False

    def check_storage_support(self) -> Dict[str, bool]:
        """Check browser storage support."""
        try:
            result = self._execute_js_action("check")
            if result:
                return result
        except Exception as e:
            logger.error(f"Failed to check storage support: {e}")

        return {"localStorage": False, "cookies": False, "supported": False}

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        return {
            "username": st.session_state.get("username", ""),
            "email": st.session_state.get("useremail", ""),
            "role": st.session_state.get("role", ""),
            "authenticated": self.is_user_authenticated(),
            "session_expiry": st.session_state.get("session_expiry", 0),
            "time_remaining": max(0, st.session_state.get("session_expiry", 0) - time.time()),
            "session_id": self._session_id
        }


# Global instance management
_global_session_manager = None


def get_streamlit_cloud_session_manager() -> StreamlitCloudSessionManager:
    """Get the global session manager instance."""
    global _global_session_manager

    if _global_session_manager is None:
        _global_session_manager = StreamlitCloudSessionManager()

    return _global_session_manager

# Convenience functions for easy integration


def save_user_session_cloud(username: str, email: str, role: str) -> bool:
    """Save user session using Streamlit Cloud session manager."""
    return get_streamlit_cloud_session_manager().save_user_session(username, email, role)


def load_user_session_cloud() -> bool:
    """Load user session using Streamlit Cloud session manager."""
    return get_streamlit_cloud_session_manager().load_user_session()


def clear_user_session_cloud() -> bool:
    """Clear user session using Streamlit Cloud session manager."""
    return get_streamlit_cloud_session_manager().clear_user_session()


def is_user_authenticated_cloud() -> bool:
    """Check if user is authenticated using Streamlit Cloud session manager."""
    return get_streamlit_cloud_session_manager().is_user_authenticated()


def get_session_info_cloud() -> Dict[str, Any]:
    """Get session information using Streamlit Cloud session manager."""
    return get_streamlit_cloud_session_manager().get_session_info()

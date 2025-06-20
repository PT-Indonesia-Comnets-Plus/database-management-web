"""
Enhanced session management with cookies backup and robust fallback.
Designed to handle cookies timeout and provide persistent login experience.
"""

import streamlit as st
import logging
import time
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class EnhancedSessionManager:
    """
    Enhanced session manager that provides robust user session persistence
    with multiple fallback mechanisms.
    """
    
    def __init__(self):
        self._cookies = None
        self._cookies_ready = False
        self._initialization_attempted = False
        
    def _initialize_cookies(self) -> bool:
        """Initialize cookies with proper error handling and timeout."""
        if self._initialization_attempted and self._cookies is not None:
            return self._cookies_ready
            
        self._initialization_attempted = True
        
        try:
            from streamlit_cookies_manager import EncryptedCookieManager
            
            # Get password from secrets with fallback
            cookie_password = "super_secret_key"
            if hasattr(st, 'secrets') and 'cookie_password' in st.secrets:
                cookie_password = st.secrets.cookie_password
            
            # Initialize cookies
            self._cookies = EncryptedCookieManager(
                prefix="Iconnet_Corp_App_v1",
                password=cookie_password
            )
            
            # Check if cookies are ready with reasonable timeout
            max_wait = 10  # 10 seconds timeout
            start_time = time.time()
            
            while not self._cookies.ready() and (time.time() - start_time) < max_wait:
                time.sleep(0.3)
            
            self._cookies_ready = self._cookies.ready()
            
            if self._cookies_ready:
                logger.info("Cookies manager initialized successfully")
                return True
            else:
                logger.warning("Cookies manager timeout - proceeding with session-only mode")
                return False
                
        except ImportError:
            logger.warning("streamlit_cookies_manager not available - using session-only mode")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize cookies manager: {e}")
            return False
    
    def save_user_session(self, username: str, email: str, role: str) -> bool:
        """
        Save user session data with multiple persistence methods.
        
        Args:
            username: User's username
            email: User's email
            role: User's role
            
        Returns:
            bool: True if saved successfully to any method
        """
        saved_successfully = False
        
        # Method 1: Save to session state (always works)
        try:
            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False
            st.session_state.last_login_time = time.time()
            saved_successfully = True
            logger.info(f"User session saved to session state: {username}")
        except Exception as e:
            logger.error(f"Failed to save to session state: {e}")
        
        # Method 2: Save to cookies (if available)
        if self._initialize_cookies() and self._cookies_ready:
            try:
                self._cookies["username"] = username
                self._cookies["email"] = email
                self._cookies["role"] = role
                self._cookies["signout"] = "False"
                self._cookies["last_login_time"] = str(time.time())
                self._cookies.save()
                logger.info(f"User session saved to cookies: {username}")
            except Exception as e:
                logger.warning(f"Failed to save to cookies: {e}")
        
        # Method 3: Save to browser localStorage backup (via Streamlit components)
        try:
            session_data = {
                "username": username,
                "email": email,
                "role": role,
                "signout": False,
                "last_login_time": time.time()
            }
            # Store as backup in session state for persistence across reloads
            st.session_state._backup_user_data = session_data
        except Exception as e:
            logger.warning(f"Failed to save backup session data: {e}")
        
        return saved_successfully
    
    def load_user_session(self) -> bool:
        """
        Load user session data from any available persistence method.
        
        Returns:
            bool: True if user session was successfully restored
        """
        user_loaded = False
        
        # Method 1: Try to load from cookies first (most persistent)
        if self._initialize_cookies() and self._cookies_ready:
            user_loaded = self._load_from_cookies()
            if user_loaded:
                logger.info("User session restored from cookies")
                return True
        
        # Method 2: Try to load from session state backup
        if not user_loaded:
            user_loaded = self._load_from_session_backup()
            if user_loaded:
                logger.info("User session restored from session backup")
                return True
        
        # Method 3: Check if session state already has valid data
        if not user_loaded:
            user_loaded = self._validate_current_session()
            if user_loaded:
                logger.info("User session validated from current session state")
                return True
        
        # No valid session found
        logger.debug("No valid user session found - user needs to login")
        self._ensure_clean_session_state()
        return False
    
    def _load_from_cookies(self) -> bool:
        """Load user data from cookies."""
        try:
            username = self._cookies.get("username", "")
            email = self._cookies.get("email", "")
            role = self._cookies.get("role", "")
            signout_status = self._cookies.get("signout", "True")
            last_login_time = self._cookies.get("last_login_time", "0")
            
            # Validate session age (expire after 7 days)
            try:
                login_time = float(last_login_time)
                if time.time() - login_time > (7 * 24 * 60 * 60):  # 7 days
                    logger.info("Session expired (7 days), clearing cookies")
                    self.clear_user_session()
                    return False
            except ValueError:
                logger.warning("Invalid login time in cookies")
            
            if username and email and signout_status == "False":
                st.session_state.username = username
                st.session_state.useremail = email
                st.session_state.role = role
                st.session_state.signout = False
                st.session_state.last_login_time = login_time
                return True
                
        except Exception as e:
            logger.error(f"Error loading from cookies: {e}")
        
        return False
    
    def _load_from_session_backup(self) -> bool:
        """Load user data from session state backup."""
        try:
            backup_data = st.session_state.get('_backup_user_data')
            if backup_data and isinstance(backup_data, dict):
                username = backup_data.get("username", "")
                email = backup_data.get("email", "")
                role = backup_data.get("role", "")
                signout = backup_data.get("signout", True)
                last_login_time = backup_data.get("last_login_time", 0)
                
                # Validate session age
                if time.time() - last_login_time > (7 * 24 * 60 * 60):  # 7 days
                    logger.info("Backup session expired")
                    return False
                
                if username and email and not signout:
                    st.session_state.username = username
                    st.session_state.useremail = email
                    st.session_state.role = role
                    st.session_state.signout = False
                    st.session_state.last_login_time = last_login_time
                    return True
                    
        except Exception as e:
            logger.error(f"Error loading from session backup: {e}")
        
        return False
    
    def _validate_current_session(self) -> bool:
        """Validate current session state data."""
        try:
            username = st.session_state.get("username", "")
            email = st.session_state.get("useremail", "")
            signout = st.session_state.get("signout", True)
            
            return bool(username.strip()) and bool(email.strip()) and not signout
            
        except Exception as e:
            logger.error(f"Error validating current session: {e}")
            return False
    
    def _ensure_clean_session_state(self):
        """Ensure session state has clean default values."""
        defaults = {
            "username": "",
            "useremail": "",
            "role": "",
            "signout": True,
            "last_login_time": 0
        }
        
        for key, default_value in defaults.items():
            if not hasattr(st.session_state, key):
                setattr(st.session_state, key, default_value)
    
    def clear_user_session(self) -> bool:
        """Clear user session from all persistence methods."""
        cleared = False
        
        # Clear session state
        try:
            st.session_state.username = ""
            st.session_state.useremail = ""
            st.session_state.role = ""
            st.session_state.signout = True
            if hasattr(st.session_state, '_backup_user_data'):
                delattr(st.session_state, '_backup_user_data')
            cleared = True
            logger.info("Session state cleared")
        except Exception as e:
            logger.error(f"Error clearing session state: {e}")
        
        # Clear cookies
        if self._cookies_ready:
            try:
                self._cookies["username"] = ""
                self._cookies["email"] = ""
                self._cookies["role"] = ""
                self._cookies["signout"] = "True"
                self._cookies["last_login_time"] = "0"
                self._cookies.save()
                logger.info("Cookies cleared")
            except Exception as e:
                logger.warning(f"Error clearing cookies: {e}")
        
        return cleared
    
    def is_user_authenticated(self) -> bool:
        """
        Check if user is currently authenticated.
        
        Returns:
            bool: True if user is authenticated
        """
        try:
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)
            
            is_auth = bool(username.strip()) and not signout
            
            if is_auth:
                logger.debug(f"User authenticated: {username}")
            else:
                logger.debug("User not authenticated")
                
            return is_auth
            
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False


# Global instance
_session_manager = None

def get_session_manager() -> EnhancedSessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = EnhancedSessionManager()
    return _session_manager


# Compatibility functions for existing code
def save_user_to_cookie(username: str, email: str, role: str) -> bool:
    """Compatibility function for existing code."""
    return get_session_manager().save_user_session(username, email, role)


def load_cookie_to_session() -> bool:
    """Compatibility function for existing code."""
    return get_session_manager().load_user_session()


def clear_user_cookie() -> bool:
    """Compatibility function for existing code."""
    return get_session_manager().clear_user_session()

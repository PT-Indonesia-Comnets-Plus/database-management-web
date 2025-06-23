"""
Cloud-optimized session storage for Streamlit applications.
This module provides persistent session storage that works reliably on Streamlit Cloud.
"""

import streamlit as st
import json
import logging
import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CloudSessionStorage:
    """
    Cloud-optimized session storage that uses multiple storage methods
    for maximum reliability on Streamlit Cloud.
    """
    
    def __init__(self, storage_key: str = "iconnet_session", 
                 timeout_hours: int = 7):
        """
        Initialize cloud session storage.
        
        Args:
            storage_key: Base key for storage
            timeout_hours: Session timeout in hours
        """
        self.storage_key = storage_key
        self.timeout_seconds = timeout_hours * 3600
        self.session_id = self._generate_session_id()
        
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        try:
            # Create session ID based on timestamp and random data
            import secrets
            timestamp = str(int(time.time()))
            random_data = secrets.token_hex(8)
            session_data = f"{timestamp}_{random_data}"
            return hashlib.md5(session_data.encode()).hexdigest()[:16]
        except Exception:
            # Fallback if secrets not available
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
    
    def _get_storage_key(self, key: str) -> str:
        """Get the full storage key."""
        return f"{self.storage_key}_{key}_{self.session_id}"
    
    def save_user_session(self, username: str, email: str, role: str) -> bool:
        """
        Save user session data using multiple storage methods.
        
        Args:
            username: User's username
            email: User's email
            role: User's role
            
        Returns:
            bool: True if session was saved successfully
        """
        try:
            current_time = time.time()
            session_data = {
                'username': username,
                'email': email,
                'role': role,
                'signout': False,
                'login_timestamp': current_time,
                'session_expiry': current_time + self.timeout_seconds,
                'session_id': self.session_id,
                'last_activity': current_time
            }
            
            # Method 1: Store in st.session_state (primary)
            for key, value in session_data.items():
                st.session_state[key] = value
            
            # Method 2: Store as encoded string in session_state for persistence
            try:
                encoded_session = json.dumps(session_data)
                st.session_state[f"_encoded_session_{self.session_id}"] = encoded_session
            except Exception as e:
                logger.warning(f"Failed to encode session data: {e}")
            
            # Method 3: Store in browser's sessionStorage via JavaScript (if available)
            try:
                self._save_to_browser_storage(session_data)
            except Exception as e:
                logger.debug(f"Browser storage not available: {e}")
            
            logger.info(f"User session saved for: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user session: {e}")
            return False
    
    def load_user_session(self) -> bool:
        """
        Load user session data from available storage methods.
        
        Returns:
            bool: True if valid session was loaded
        """
        try:
            # Method 1: Try to load from st.session_state
            session_data = self._load_from_session_state()
            
            # Method 2: Try to load from encoded session data
            if not session_data:
                session_data = self._load_from_encoded_session()
            
            # Method 3: Try to load from browser storage
            if not session_data:
                session_data = self._load_from_browser_storage()
            
            if session_data and self._is_session_valid(session_data):
                # Update session state with loaded data
                for key, value in session_data.items():
                    st.session_state[key] = value
                
                # Update last activity
                st.session_state.last_activity = time.time()
                
                logger.info(f"User session loaded: {session_data.get('username', 'Unknown')}")
                return True
            
            # No valid session found, set defaults
            self._set_default_session_state()
            return False
            
        except Exception as e:
            logger.error(f"Failed to load user session: {e}")
            self._set_default_session_state()
            return False
    
    def clear_user_session(self) -> bool:
        """
        Clear user session from all storage methods.
        
        Returns:
            bool: True if session was cleared successfully
        """
        try:
            # Clear session state
            session_keys = [
                'username', 'useremail', 'role', 'signout',
                'login_timestamp', 'session_expiry', 'session_id',
                'last_activity', 'user_uid'
            ]
            
            for key in session_keys:
                if key in st.session_state:
                    if key == 'signout':
                        st.session_state[key] = True
                    elif key in ['username', 'useremail', 'role']:
                        st.session_state[key] = ""
                    else:
                        del st.session_state[key]
            
            # Clear encoded session data
            encoded_key = f"_encoded_session_{self.session_id}"
            if encoded_key in st.session_state:
                del st.session_state[encoded_key]
            
            # Clear browser storage
            try:
                self._clear_browser_storage()
            except Exception as e:
                logger.debug(f"Failed to clear browser storage: {e}")
            
            logger.info("User session cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear user session: {e}")
            return False
    
    def is_session_valid(self) -> bool:
        """
        Check if current session is valid and not expired.
        
        Returns:
            bool: True if session is valid
        """
        try:
            username = st.session_state.get('username', '')
            signout = st.session_state.get('signout', True)
            session_expiry = st.session_state.get('session_expiry', 0)
            
            if not username or signout:
                return False
            
            current_time = time.time()
            if session_expiry < current_time:
                logger.info(f"Session expired for user: {username}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check session validity: {e}")
            return False
    
    def refresh_session(self) -> bool:
        """
        Refresh session expiry time.
        
        Returns:
            bool: True if session was refreshed successfully
        """
        try:
            if self.is_session_valid():
                current_time = time.time()
                new_expiry = current_time + self.timeout_seconds
                
                st.session_state.session_expiry = new_expiry
                st.session_state.last_activity = current_time
                
                # Update encoded session if exists
                try:
                    encoded_key = f"_encoded_session_{self.session_id}"
                    if encoded_key in st.session_state:
                        session_data = json.loads(st.session_state[encoded_key])
                        session_data['session_expiry'] = new_expiry
                        session_data['last_activity'] = current_time
                        st.session_state[encoded_key] = json.dumps(session_data)
                except Exception as e:
                    logger.debug(f"Failed to update encoded session: {e}")
                
                logger.debug(f"Session refreshed for: {st.session_state.get('username')}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to refresh session: {e}")
            return False
    
    def _load_from_session_state(self) -> Optional[Dict[str, Any]]:
        """Load session data directly from session_state."""
        try:
            required_keys = ['username', 'useremail', 'role', 'signout']
            if all(key in st.session_state for key in required_keys):
                return {
                    'username': st.session_state.get('username', ''),
                    'email': st.session_state.get('useremail', ''),
                    'role': st.session_state.get('role', ''),
                    'signout': st.session_state.get('signout', True),
                    'login_timestamp': st.session_state.get('login_timestamp', 0),
                    'session_expiry': st.session_state.get('session_expiry', 0),
                    'session_id': st.session_state.get('session_id', ''),
                    'last_activity': st.session_state.get('last_activity', 0)
                }
        except Exception as e:
            logger.debug(f"Failed to load from session state: {e}")
        
        return None
    
    def _load_from_encoded_session(self) -> Optional[Dict[str, Any]]:
        """Load session data from encoded session string."""
        try:
            encoded_key = f"_encoded_session_{self.session_id}"
            encoded_session = st.session_state.get(encoded_key)
            
            if encoded_session:
                return json.loads(encoded_session)
        except Exception as e:
            logger.debug(f"Failed to load from encoded session: {e}")
        
        return None
    
    def _save_to_browser_storage(self, session_data: Dict[str, Any]) -> None:
        """Save session data to browser's sessionStorage (if available)."""
        try:
            # This would require JavaScript integration
            # For now, we'll skip this as it requires additional setup
            pass
        except Exception as e:
            logger.debug(f"Browser storage save failed: {e}")
    
    def _load_from_browser_storage(self) -> Optional[Dict[str, Any]]:
        """Load session data from browser's sessionStorage (if available)."""
        try:
            # This would require JavaScript integration
            # For now, we'll skip this as it requires additional setup
            pass
        except Exception as e:
            logger.debug(f"Browser storage load failed: {e}")
        
        return None
    
    def _clear_browser_storage(self) -> None:
        """Clear session data from browser's sessionStorage."""
        try:
            # This would require JavaScript integration
            # For now, we'll skip this as it requires additional setup
            pass
        except Exception as e:
            logger.debug(f"Browser storage clear failed: {e}")
    
    def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session data is valid and not expired."""
        try:
            username = session_data.get('username', '')
            signout = session_data.get('signout', True)
            session_expiry = session_data.get('session_expiry', 0)
            
            if not username or signout:
                return False
            
            current_time = time.time()
            if session_expiry < current_time:
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Session validation failed: {e}")
            return False
    
    def _set_default_session_state(self) -> None:
        """Set default values in session state."""
        defaults = {
            'username': '',
            'useremail': '',
            'role': '',
            'signout': True
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value


# Global instance
_cloud_session_storage = None


def get_cloud_session_storage() -> CloudSessionStorage:
    """Get the global cloud session storage instance."""
    global _cloud_session_storage
    
    if _cloud_session_storage is None:
        _cloud_session_storage = CloudSessionStorage()
    
    return _cloud_session_storage


# Utility functions for easy integration
def save_user_session_cloud(username: str, email: str, role: str) -> bool:
    """Save user session using cloud storage."""
    return get_cloud_session_storage().save_user_session(username, email, role)


def load_user_session_cloud() -> bool:
    """Load user session using cloud storage."""
    return get_cloud_session_storage().load_user_session()


def clear_user_session_cloud() -> bool:
    """Clear user session using cloud storage."""
    return get_cloud_session_storage().clear_user_session()


def is_user_session_valid_cloud() -> bool:
    """Check if user session is valid using cloud storage."""
    return get_cloud_session_storage().is_session_valid()


def refresh_user_session_cloud() -> bool:
    """Refresh user session using cloud storage."""
    return get_cloud_session_storage().refresh_session()

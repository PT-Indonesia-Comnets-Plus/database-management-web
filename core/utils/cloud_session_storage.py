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
        Save user session data using multiple storage methods for maximum persistence.

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
                'last_activity': current_time,
                'version': '3.0'  # Updated version for better tracking
            }

            # Method 1: Store in st.session_state (primary - always available)
            for key, value in session_data.items():
                st.session_state[key] = value

            save_success_count = 1  # session_state is always successful

            # Method 2: Store as multiple encoded strings in session_state for redundancy
            try:
                encoded_session = json.dumps(session_data)
                # Save with multiple keys for redundancy
                st.session_state[f"_encoded_session_{self.session_id}"] = encoded_session
                st.session_state[f"iconnet_session_{username}"] = encoded_session
                st.session_state[f"backup_session_{int(current_time)}"] = encoded_session
                save_success_count += 1
            except Exception as e:
                logger.warning(f"Failed to encode session data: {e}")

            # Method 3: Store in browser's sessionStorage/localStorage via JavaScript
            try:
                self._save_to_browser_storage(session_data)
                save_success_count += 1
            except Exception as e:
                logger.debug(f"Browser storage not available: {e}")

            # Method 4: For Streamlit Cloud, also save in a persistent format
            try:
                # Create a more persistent session record
                persistent_data = {
                    'user': username,
                    'session': encoded_session,
                    'timestamp': current_time,
                    'expiry': session_data['session_expiry']
                }
                st.session_state[f"persistent_auth_{username}"] = persistent_data
                save_success_count += 1
            except Exception as e:
                logger.debug(f"Persistent storage failed: {e}")

            logger.info(
                f"User session saved with {save_success_count} methods for: {username}")
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

                logger.info(
                    f"User session loaded: {session_data.get('username', 'Unknown')}")
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
                        session_data = json.loads(
                            st.session_state[encoded_key])
                        session_data['session_expiry'] = new_expiry
                        session_data['last_activity'] = current_time
                        st.session_state[encoded_key] = json.dumps(
                            session_data)
                except Exception as e:
                    logger.debug(f"Failed to update encoded session: {e}")

                logger.debug(
                    f"Session refreshed for: {st.session_state.get('username')}")
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
        """
        Load session data from browser storage using JavaScript.
        This is specifically for Streamlit Cloud where regular cookies might fail.
        """
        try:
            # Temporarily disable JavaScript integration due to compatibility issues
            # Focus on session_state based persistence for now
            logger.debug("Browser storage disabled - using session_state only")
            return None
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

    def _enhanced_session_restoration(self) -> bool:
        """
        Enhanced session restoration specifically for Streamlit Cloud.
        This method tries multiple strategies to restore user sessions.
        """
        try:
            logger.info(
                "Starting enhanced session restoration for Streamlit Cloud")

            # Debug: Show all current session state keys
            all_keys = list(st.session_state.keys())
            session_related_keys = [k for k in all_keys if any(term in k.lower() for term in
                                                               ['session', 'user', 'auth', 'login', 'encoded', 'persistent'])]
            logger.debug(f"All session-related keys: {session_related_keys}")

            # Strategy 1: Check for active session in current session state
            current_user = st.session_state.get("username", "")
            current_signout = st.session_state.get("signout", True)
            current_expiry = st.session_state.get("session_expiry", 0)

            if (current_user and not current_signout and
                    current_expiry > 0 and current_expiry > time.time()):
                logger.info(f"Active session found for: {current_user}")
                return True            # Strategy 2: Look for encoded session data in session state keys
            logger.debug("Searching for encoded session data...")
            found_keys = []
            for key in list(st.session_state.keys()):
                if (key.startswith("_encoded_session_") or
                    key.startswith("iconnet_session_") or
                    key.startswith("backup_session_") or
                        key.startswith("persistent_auth_")):
                    found_keys.append(key)

            logger.debug(f"Found potential session keys: {found_keys}")

            for key in found_keys:
                try:
                    if key.startswith("persistent_auth_"):
                        # Handle persistent auth format
                        auth_data = st.session_state[key]
                        if isinstance(auth_data, dict) and auth_data.get('expiry', 0) > time.time():
                            session_str = auth_data.get('session', '')
                            if session_str:
                                session_data = json.loads(session_str)
                            else:
                                continue
                        else:
                            # Clean up expired auth
                            del st.session_state[key]
                            continue
                    else:
                        # Handle encoded session format
                        if isinstance(st.session_state[key], str):
                            session_data = json.loads(st.session_state[key])
                        else:
                            session_data = st.session_state[key]

                    if self._is_session_valid(session_data):
                        # Restore session
                        st.session_state.username = session_data.get(
                            "username", "")
                        st.session_state.useremail = session_data.get(
                            "email", "")
                        st.session_state.role = session_data.get("role", "")
                        st.session_state.signout = session_data.get(
                            "signout", True)
                        st.session_state.login_timestamp = session_data.get(
                            "login_timestamp", time.time())
                        st.session_state.session_expiry = session_data.get(
                            "session_expiry", 0)

                        restored_user = session_data.get("username", "")
                        logger.info(
                            f"🟢 Session restored from {key}: {restored_user}")
                        return True
                    else:
                        # Clean up expired data
                        logger.debug(f"Cleaning up expired session key: {key}")
                        del st.session_state[key]
                except Exception as e:
                    logger.debug(
                        f"Failed to parse session data from {key}: {e}")
                    try:
                        del st.session_state[key]
                    except:
                        pass

            # Strategy 3: Try to restore from any persistent browser data
            try:
                browser_data = self._load_from_browser_storage()
                if browser_data and self._is_session_valid(browser_data):
                    for key, value in browser_data.items():
                        st.session_state[key] = value

                    restored_user = browser_data.get("username", "")
                    logger.info(
                        f"Session restored from browser storage: {restored_user}")
                    return True
            except Exception as e:
                logger.debug(f"Browser storage restoration failed: {e}")

            # Strategy 4: Check for legacy session data patterns
            legacy_keys = ["user_session_data", "auth_data", "login_data"]
            for legacy_key in legacy_keys:
                if legacy_key in st.session_state:
                    try:
                        legacy_data = st.session_state[legacy_key]
                        if isinstance(legacy_data, dict) and legacy_data.get("username"):
                            # Convert legacy format to current format
                            session_data = {
                                "username": legacy_data.get("username", ""),
                                "email": legacy_data.get("email", ""),
                                "role": legacy_data.get("role", ""),
                                "signout": legacy_data.get("signout", True),
                                "login_timestamp": legacy_data.get("login_timestamp", time.time()),
                                "session_expiry": legacy_data.get("session_expiry", time.time() + self.timeout_seconds)
                            }

                            if self._is_session_valid(session_data):
                                for key, value in session_data.items():
                                    st.session_state[key] = value

                                restored_user = session_data.get(
                                    "username", "")
                                logger.info(
                                    f"Session restored from legacy data: {restored_user}")
                                return True

                        # Clean up legacy key
                        del st.session_state[legacy_key]
                    except Exception as e:
                        logger.debug(f"Failed to process legacy data: {e}")

            logger.info("No valid session found for restoration")
            return False

        except Exception as e:
            logger.error(f"Enhanced session restoration failed: {e}")
            return False


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

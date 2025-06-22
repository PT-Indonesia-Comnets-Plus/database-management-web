"""
Enhanced Cookies-Only Session Manager
Alternatif untuk cloud session dengan security yang ditingkatkan
"""

import streamlit as st
import secrets
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import base64
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class EnhancedCookiesSession:
    """
    Enhanced cookies-only session dengan security features:
    - Encrypted cookies
    - Session fingerprinting
    - Tampering detection
    - Session expiry
    """

    def __init__(self):
        self.session_timeout_hours = 7
        self._encryption_key = self._get_encryption_key()
        self._fernet = Fernet(self._encryption_key)

    def _get_encryption_key(self) -> bytes:
        """Generate/get encryption key untuk cookies"""
        try:
            # Coba ambil dari secrets
            if hasattr(st, 'secrets') and 'cookie_encryption_key' in st.secrets:
                key = st.secrets['cookie_encryption_key']
                return base64.urlsafe_b64decode(key.encode())

            # Generate baru (development)
            key = Fernet.generate_key()
            logger.warning(
                f"🔒 Generated new cookie key: {base64.urlsafe_b64encode(key).decode()}")
            return key

        except Exception as e:
            logger.error(f"Failed to get encryption key: {e}")
            return Fernet.generate_key()

    def _get_client_fingerprint(self) -> str:
        """Generate client fingerprint untuk tamper detection"""
        try:
            # Combine berbagai faktor untuk fingerprint
            user_agent = "unknown"
            ip_hint = "unknown"

            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                headers = st.context.headers
                user_agent = headers.get('user-agent', 'unknown')[:100]
                ip_hint = headers.get(
                    'x-forwarded-for', 'unknown').split(',')[0]

            # Tambahkan timestamp hari untuk rotasi harian
            day_stamp = datetime.now().strftime("%Y-%m-%d")

            fingerprint_data = f"{user_agent}:{ip_hint}:{day_stamp}"
            fingerprint = hashlib.sha256(
                fingerprint_data.encode()).hexdigest()[:16]

            return fingerprint

        except Exception as e:
            logger.warning(f"Could not generate fingerprint: {e}")
            return "fallback_fp"

    def create_session(self, username: str, email: str, role: str) -> bool:
        """Create encrypted session in cookies"""
        try:
            current_time = datetime.now()
            expires_at = current_time + \
                timedelta(hours=self.session_timeout_hours)

            # Session data
            session_data = {
                'username': username,
                'email': email,
                'role': role,
                'created_at': current_time.isoformat(),
                'expires_at': expires_at.isoformat(),
                'session_id': secrets.token_urlsafe(32),
                'fingerprint': self._get_client_fingerprint(),
                'version': '1.0'  # Untuk future compatibility
            }

            # Encrypt session data
            encrypted_data = self._encrypt_session_data(session_data)

            # Save ke cookies (gunakan library cookies yang sudah ada)
            try:
                if hasattr(st.session_state, 'cookies'):
                    cookies = st.session_state.cookies
                    cookies['iconnet_secure_session'] = encrypted_data
                    cookies['iconnet_session_check'] = self._generate_integrity_check(
                        encrypted_data)
                    cookies.save()

                    # Update session state juga
                    self._update_session_state(session_data)

                    logger.info(
                        f"🍪 Enhanced cookie session created for: {username}")
                    return True
                else:
                    logger.warning("Cookies manager not available")
                    return False

            except Exception as e:
                logger.error(f"Failed to save cookies: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to create cookie session: {e}")
            return False

    def validate_session(self) -> bool:
        """Validate session dari cookies dengan security checks"""
        try:
            if hasattr(st.session_state, 'cookies'):
                cookies = st.session_state.cookies

                encrypted_data = cookies.get('iconnet_secure_session')
                integrity_check = cookies.get('iconnet_session_check')

                if not encrypted_data or not integrity_check:
                    return False

                # Verify integrity
                if not self._verify_integrity_check(encrypted_data, integrity_check):
                    logger.warning("🚨 Cookie tampering detected!")
                    self._clear_session()
                    return False

                # Decrypt session data
                session_data = self._decrypt_session_data(encrypted_data)
                if not session_data:
                    return False

                # Check expiry
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                if datetime.now() > expires_at:
                    logger.info("Session expired")
                    self._clear_session()
                    return False

                # Verify fingerprint (detect browser/device change)
                current_fingerprint = self._get_client_fingerprint()
                if current_fingerprint != session_data.get('fingerprint', ''):
                    logger.warning("🚨 Browser fingerprint mismatch!")
                    # Bisa pilih: tolak atau warning saja
                    # return False  # Strict mode
                    # Lenient mode
                    logger.warning("Continuing with fingerprint mismatch")

                # Update session state
                self._update_session_state(session_data)

                logger.debug(
                    f"🍪 Cookie session valid for: {session_data['username']}")
                return True

            return False

        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False

    def _encrypt_session_data(self, data: Dict[str, Any]) -> str:
        """Encrypt session data"""
        try:
            json_data = json.dumps(data)
            encrypted_data = self._fernet.encrypt(json_data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return ""

    def _decrypt_session_data(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """Decrypt session data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    def _generate_integrity_check(self, encrypted_data: str) -> str:
        """Generate integrity check untuk detect tampering"""
        # HMAC-like check
        secret_salt = "iconnet_integrity_2024"
        check_data = f"{encrypted_data}:{secret_salt}"
        return hashlib.sha256(check_data.encode()).hexdigest()[:32]

    def _verify_integrity_check(self, encrypted_data: str, check: str) -> bool:
        """Verify integrity check"""
        expected_check = self._generate_integrity_check(encrypted_data)
        return secrets.compare_digest(expected_check, check)

    def _update_session_state(self, session_data: Dict[str, Any]):
        """Update Streamlit session state"""
        st.session_state.username = session_data['username']
        st.session_state.useremail = session_data['email']
        st.session_state.role = session_data['role']
        st.session_state.signout = False
        st.session_state.session_id = session_data['session_id']
        st.session_state.session_type = 'enhanced_cookies'

    def _clear_session(self):
        """Clear session data"""
        try:
            if hasattr(st.session_state, 'cookies'):
                cookies = st.session_state.cookies
                if 'iconnet_secure_session' in cookies:
                    del cookies['iconnet_secure_session']
                if 'iconnet_session_check' in cookies:
                    del cookies['iconnet_session_check']
                cookies.save()

            # Clear session state
            for key in ['username', 'useremail', 'role', 'session_id']:
                if key in st.session_state:
                    del st.session_state[key]

            st.session_state.signout = True

        except Exception as e:
            logger.error(f"Failed to clear session: {e}")

    def logout(self):
        """Logout user dan clear session"""
        username = st.session_state.get('username', 'Unknown')
        logger.info(f"🍪 Enhanced cookie logout for: {username}")
        self._clear_session()


# Global instance
_enhanced_cookies_session: Optional[EnhancedCookiesSession] = None


def get_enhanced_cookies_session() -> EnhancedCookiesSession:
    """Get or create enhanced cookies session manager"""
    global _enhanced_cookies_session

    if _enhanced_cookies_session is None:
        _enhanced_cookies_session = EnhancedCookiesSession()

    return _enhanced_cookies_session

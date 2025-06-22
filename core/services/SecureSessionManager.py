"""
Secure Session Manager - Enhanced security for user sessions
Addresses session hijacking, weak session IDs, and ensures proper session isolation
"""

import streamlit as st
import secrets
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import ipaddress
from cryptography.fernet import Fernet
import base64
import os

logger = logging.getLogger(__name__)


@dataclass
class SessionSecurityConfig:
    """Configuration for session security settings"""
    max_sessions_per_user: int = 3
    session_timeout_hours: int = 7
    ip_validation_enabled: bool = True
    browser_fingerprint_enabled: bool = True
    session_rotation_hours: int = 2
    encryption_enabled: bool = True
    suspicious_activity_detection: bool = True


class SecureSessionManager:
    """
    Enhanced session manager with security features:
    - Cryptographic session IDs
    - IP address binding
    - Browser fingerprint validation
    - Session encryption
    - Concurrent session limits
    - Activity monitoring
    """

    def __init__(self, db_pool=None, config: SessionSecurityConfig = None):
        self.db_pool = db_pool
        self.config = config or SessionSecurityConfig()
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(
            self._encryption_key) if self.config.encryption_enabled else None

        # Initialize security tracking
        if "security_violations" not in st.session_state:
            st.session_state.security_violations = 0

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for session data"""
        try:
            # Try to get from secrets first (production)
            if hasattr(st, 'secrets') and 'session_encryption_key' in st.secrets:
                key = st.secrets['session_encryption_key']
                return base64.urlsafe_b64decode(key.encode())

            # Fallback to environment variable
            env_key = os.getenv('ICONNET_SESSION_KEY')
            if env_key:
                return base64.urlsafe_b64decode(env_key.encode())

            # Generate new key (development only - log warning)
            logger.warning(
                "🔒 Generating new session encryption key - NOT FOR PRODUCTION!")
            key = Fernet.generate_key()
            logger.warning(
                f"🔒 Store this key in secrets.toml: session_encryption_key = \"{base64.urlsafe_b64encode(key).decode()}\"")
            return key

        except Exception as e:
            logger.error(f"Failed to initialize encryption key: {e}")
            # Fallback to insecure key (with warning)
            logger.warning(
                "🚨 USING INSECURE FALLBACK ENCRYPTION KEY - REPLACE IMMEDIATELY!")
            return Fernet.generate_key()

    def generate_secure_session_id(self, username: str, ip_address: str, user_agent: str) -> str:
        """Generate cryptographically secure session ID bound to user context"""
        try:
            # Create session context for binding
            timestamp = str(datetime.now().timestamp())
            random_token = secrets.token_urlsafe(32)

            # Create binding data (for validation later)
            binding_data = f"{username}:{ip_address}:{user_agent}:{timestamp}"
            binding_hash = hashlib.sha256(
                binding_data.encode()).hexdigest()[:16]

            # Combine random token with binding hash
            session_id = f"{random_token}.{binding_hash}.{secrets.token_urlsafe(8)}"

            logger.info(
                f"🔐 Generated secure session ID for user: {username[:4]}***")
            return session_id

        except Exception as e:
            logger.error(f"Failed to generate secure session ID: {e}")
            # Fallback to less secure but functional ID
            return f"fallback_{secrets.token_urlsafe(24)}"

    def get_client_context(self) -> Dict[str, str]:
        """Extract client context for session binding and validation"""
        context = {
            'ip_address': 'unknown',
            'user_agent': 'unknown',
            'browser_fingerprint': 'unknown',
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Get IP address from Streamlit context
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                headers = st.context.headers
                # Try various headers for real IP
                ip_headers = ['x-forwarded-for', 'x-real-ip',
                              'cf-connecting-ip', 'x-client-ip']
                for header in ip_headers:
                    if header in headers:
                        ip = headers[header].split(',')[0].strip()
                        if self._is_valid_ip(ip):
                            context['ip_address'] = ip
                            break

                # Get User-Agent
                if 'user-agent' in headers:
                    # Limit length
                    context['user_agent'] = headers['user-agent'][:200]

            # Generate browser fingerprint
            context['browser_fingerprint'] = self._generate_browser_fingerprint(
                context['ip_address'], context['user_agent']
            )

        except Exception as e:
            logger.warning(f"Could not extract full client context: {e}")

        return context

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _generate_browser_fingerprint(self, ip: str, user_agent: str) -> str:
        """Generate enhanced browser fingerprint for session binding"""
        try:
            # Combine multiple factors for fingerprinting
            fingerprint_data = f"{ip}:{user_agent}:{datetime.now().date()}"
            fingerprint = hashlib.sha256(
                fingerprint_data.encode()).hexdigest()[:24]

            # Store in session state for consistency during session
            if "browser_fingerprint" not in st.session_state:
                st.session_state.browser_fingerprint = fingerprint

            return fingerprint

        except Exception as e:
            logger.warning(f"Could not generate browser fingerprint: {e}")
            return f"fallback_{secrets.token_urlsafe(12)}"

    def _encrypt_session_data(self, data: Dict[str, Any]) -> str:
        """Encrypt session data before storage"""
        if not self._fernet:
            return json.dumps(data)

        try:
            json_data = json.dumps(data)
            encrypted_data = self._fernet.encrypt(json_data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt session data: {e}")
            return json.dumps(data)  # Fallback to unencrypted

    def _decrypt_session_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt session data after loading"""
        if not self._fernet:
            try:
                return json.loads(encrypted_data)
            except:
                return {}

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt session data: {e}")
            # Try fallback to unencrypted
            try:
                return json.loads(encrypted_data)
            except:
                return {}

    def create_secure_session(self, username: str, email: str, role: str,
                              user_id: str = None) -> Tuple[bool, str]:
        """Create a new secure session with all security measures"""
        try:
            # Get client context
            client_context = self.get_client_context()

            # Check concurrent session limit
            if not self._check_session_limit(username):
                return False, "Too many active sessions. Please logout from other devices."

            # Generate secure session ID
            session_id = self.generate_secure_session_id(
                username,
                client_context['ip_address'],
                client_context['user_agent']
            )

            # Create session data
            current_time = datetime.now()
            session_data = {
                'session_id': session_id,
                'username': username,
                'email': email,
                'role': role,
                'user_id': user_id or username,
                'created_at': current_time.isoformat(),
                'last_activity': current_time.isoformat(),
                'expires_at': (current_time + timedelta(hours=self.config.session_timeout_hours)).isoformat(),
                'ip_address': client_context['ip_address'],
                'user_agent': client_context['user_agent'],
                'browser_fingerprint': client_context['browser_fingerprint'],
                'security_level': 'high',
                'is_active': True
            }

            # Save to database (encrypted)
            if self._save_secure_session_to_db(session_data):
                # Update Streamlit session state
                self._update_session_state(session_data)

                # Log security event
                self._log_security_event(
                    username, 'session_created', client_context)

                logger.info(f"🔐 Secure session created for user: {username}")
                return True, "Session created successfully"
            else:
                return False, "Failed to save session data"

        except Exception as e:
            logger.error(f"Failed to create secure session: {e}")
            return False, f"Session creation failed: {e}"

    def validate_session(self, session_id: str = None) -> Tuple[bool, str]:
        """Validate current session with security checks"""
        try:
            # Get session ID from parameter or session state
            session_id = session_id or st.session_state.get('session_id')
            if not session_id:
                return False, "No session ID found"

            # Load session from database
            session_data = self._load_secure_session_from_db(session_id)
            if not session_data:
                return False, "Session not found"

            # Check expiry
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if datetime.now() > expires_at:
                self._revoke_session(session_id)
                return False, "Session expired"

            # Validate IP address (if enabled)
            if self.config.ip_validation_enabled:
                current_context = self.get_client_context()
                if current_context['ip_address'] != session_data.get('ip_address', ''):
                    self._log_security_event(
                        session_data['username'],
                        'ip_mismatch',
                        current_context,
                        suspicious=True
                    )
                    if self.config.suspicious_activity_detection:
                        self._revoke_session(session_id)
                        return False, "Session invalidated due to IP change"

            # Validate browser fingerprint (if enabled)
            if self.config.browser_fingerprint_enabled:
                current_context = self.get_client_context()
                if current_context['browser_fingerprint'] != session_data.get('browser_fingerprint', ''):
                    self._log_security_event(
                        session_data['username'],
                        'fingerprint_mismatch',
                        current_context,
                        suspicious=True
                    )
                    # Browser fingerprint mismatch is less strict than IP
                    logger.warning(
                        f"Browser fingerprint mismatch for user: {session_data['username']}")

            # Update last activity
            self._update_session_activity(session_id)

            # Check if session rotation is needed
            created_at = datetime.fromisoformat(session_data['created_at'])
            if (datetime.now() - created_at).total_seconds() > (self.config.session_rotation_hours * 3600):
                # Rotate session ID for security
                new_session_id = self.generate_secure_session_id(
                    session_data['username'],
                    session_data['ip_address'],
                    session_data['user_agent']
                )
                self._rotate_session_id(session_id, new_session_id)
                st.session_state.session_id = new_session_id
                logger.info(
                    f"🔄 Session ID rotated for user: {session_data['username']}")

            return True, "Session valid"

        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False, f"Validation error: {e}"

    def _check_session_limit(self, username: str) -> bool:
        """Check if user has exceeded concurrent session limit"""
        if not self.db_pool:
            return True

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM secure_user_sessions 
                WHERE username = %s AND is_active = true AND expires_at > NOW()
            """, (username,))

            active_sessions = cursor.fetchone()[0]
            cursor.close()
            self.db_pool.putconn(conn)

            return active_sessions < self.config.max_sessions_per_user

        except Exception as e:
            logger.error(f"Failed to check session limit: {e}")
            return True  # Allow on error

    def _save_secure_session_to_db(self, session_data: Dict[str, Any]) -> bool:
        """Save encrypted session data to database"""
        if not self.db_pool:
            return False

        try:
            # Create table if not exists
            self._ensure_secure_sessions_table()

            # Encrypt sensitive data
            encrypted_data = self._encrypt_session_data(session_data)

            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO secure_user_sessions (
                    session_id, username, encrypted_data, ip_address, 
                    user_agent, browser_fingerprint, created_at, expires_at, 
                    last_activity, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                encrypted_data = EXCLUDED.encrypted_data,
                last_activity = EXCLUDED.last_activity,
                is_active = EXCLUDED.is_active
            """, (
                session_data['session_id'],
                session_data['username'],
                encrypted_data,
                session_data['ip_address'],
                session_data['user_agent'],
                session_data['browser_fingerprint'],
                session_data['created_at'],
                session_data['expires_at'],
                session_data['last_activity'],
                session_data['is_active']
            ))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)
            return True

        except Exception as e:
            logger.error(f"Failed to save secure session: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass
            return False

    def _load_secure_session_from_db(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load and decrypt session data from database"""
        if not self.db_pool:
            return None

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT encrypted_data FROM secure_user_sessions 
                WHERE session_id = %s AND is_active = true AND expires_at > NOW()
            """, (session_id,))

            result = cursor.fetchone()
            cursor.close()
            self.db_pool.putconn(conn)

            if result:
                return self._decrypt_session_data(result[0])
            return None

        except Exception as e:
            logger.error(f"Failed to load secure session: {e}")
            return None

    def _ensure_secure_sessions_table(self):
        """Create secure sessions table if it doesn't exist"""
        if not self.db_pool:
            return

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS secure_user_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    encrypted_data TEXT NOT NULL,
                    ip_address INET,
                    user_agent TEXT,
                    browser_fingerprint VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_activity TIMESTAMP WITH TIME ZONE NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    INDEX(username),
                    INDEX(expires_at),
                    INDEX(is_active)
                )
            """)

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"Failed to create secure sessions table: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    cursor.close()
                    self.db_pool.putconn(conn)
                except:
                    pass

    def _update_session_state(self, session_data: Dict[str, Any]):
        """Update Streamlit session state with session data"""
        st.session_state.session_id = session_data['session_id']
        st.session_state.username = session_data['username']
        st.session_state.useremail = session_data['email']
        st.session_state.role = session_data['role']
        st.session_state.signout = False
        st.session_state.session_security_level = session_data.get(
            'security_level', 'standard')
        st.session_state.session_created_at = session_data['created_at']
        st.session_state.session_expires_at = session_data['expires_at']

    def _log_security_event(self, username: str, event_type: str,
                            context: Dict[str, str], suspicious: bool = False):
        """Log security-related events"""
        try:
            if not self.db_pool:
                logger.info(
                    f"🔒 Security Event: {event_type} for {username} (suspicious: {suspicious})")
                return

            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Create security log table if needed
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255),
                    event_type VARCHAR(100),
                    ip_address INET,
                    user_agent TEXT,
                    context_data JSONB,
                    is_suspicious BOOLEAN DEFAULT false,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            cursor.execute("""
                INSERT INTO security_events (
                    username, event_type, ip_address, user_agent, 
                    context_data, is_suspicious
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                username,
                event_type,
                context.get('ip_address'),
                context.get('user_agent'),
                json.dumps(context),
                suspicious
            ))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            if suspicious:
                logger.warning(
                    f"🚨 Suspicious activity: {event_type} for {username}")
                st.session_state.security_violations = st.session_state.get(
                    'security_violations', 0) + 1

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def revoke_all_user_sessions(self, username: str) -> bool:
        """Revoke all sessions for a specific user"""
        if not self.db_pool:
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE secure_user_sessions 
                SET is_active = false 
                WHERE username = %s AND is_active = true
            """, (username,))

            revoked_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            logger.info(
                f"🔒 Revoked {revoked_count} sessions for user: {username}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")
            return False

    def _revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session"""
        if not self.db_pool:
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE secure_user_sessions 
                SET is_active = false 
                WHERE session_id = %s
            """, (session_id,))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)
            return True

        except Exception as e:
            logger.error(f"Failed to revoke session: {e}")
            return False

    def get_user_active_sessions(self, username: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        if not self.db_pool:
            return []

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT session_id, ip_address, user_agent, created_at, 
                       last_activity, browser_fingerprint
                FROM secure_user_sessions 
                WHERE username = %s AND is_active = true AND expires_at > NOW()
                ORDER BY last_activity DESC
            """, (username,))

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0][:12] + '***',  # Masked for security
                    'ip_address': row[1],
                    'user_agent': row[2][:50] + '...' if len(row[2]) > 50 else row[2],
                    'created_at': row[3],
                    'last_activity': row[4],
                    'browser_fingerprint': row[5][:8] + '***'
                })

            cursor.close()
            self.db_pool.putconn(conn)
            return sessions

        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from database"""
        if not self.db_pool:
            return 0

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM secure_user_sessions 
                WHERE expires_at <= NOW() OR 
                      (is_active = false AND created_at <= NOW() - INTERVAL '7 days')
            """)

            cleaned_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            logger.info(f"🧹 Cleaned up {cleaned_count} expired sessions")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0


# Global secure session manager instance
_secure_session_manager: Optional[SecureSessionManager] = None


def get_secure_session_manager(db_pool=None, config: SessionSecurityConfig = None) -> SecureSessionManager:
    """Get or create the global secure session manager instance"""
    global _secure_session_manager

    if _secure_session_manager is None:
        _secure_session_manager = SecureSessionManager(db_pool, config)

    return _secure_session_manager

"""
Database session service for managing user sessions in the database.
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import streamlit as st

logger = logging.getLogger(__name__)


class DatabaseSessionService:
    """
    Service for managing user sessions in the database.
    Handles creation, validation, and cleanup of sessions.
    """

    def __init__(self, connection):
        """
        Initialize with database connection.

        Args:
            connection: Database connection object
        """
        self.conn = connection

    def create_session(self, username: str, email: str, role: str,
                       device_info: Dict[str, Any], ip_address: str = "127.0.0.1") -> str:
        """
        Create a new session in the database.

        Args:
            username: User's username
            email: User's email
            role: User's role
            device_info: Device information dictionary
            ip_address: User's IP address

        Returns:
            str: Session ID

        Raises:
            Exception: If session creation fails
        """
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4()).replace('-', '')

            # Calculate expiry time
            expiry_time = datetime.now() + timedelta(hours=7)  # 7 hours from now

            # Generate device fingerprint
            device_fingerprint = device_info.get(
                'fingerprint', str(uuid.uuid4())[:16])

            # Insert session into database
            query = """
                INSERT INTO cloud_user_sessions 
                (session_id, username, email, role, device_fingerprint, device_info, 
                 session_expiry, ip_address, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                session_id,
                username,
                email,
                role,
                device_fingerprint,
                str(device_info),  # Convert dict to string
                expiry_time,
                ip_address,
                True
            )

            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            cursor.close()

            logger.info(
                f"Session created for user {username}: {session_id[:8]}...")
            return session_id

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            if hasattr(self.conn, 'rollback'):
                self.conn.rollback()
            raise

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate session and return user data if valid.

        Args:
            session_id: Session ID to validate

        Returns:
            dict: User data if session is valid, None otherwise
        """
        try:
            query = """
                SELECT username, email, role, session_expiry, device_info, last_activity
                FROM cloud_user_sessions 
                WHERE session_id = %s AND is_active = TRUE
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (session_id,))
            result = cursor.fetchone()
            cursor.close()

            if not result:
                logger.debug(f"Session not found: {session_id[:8]}...")
                return None

            username, email, role, session_expiry, device_info, last_activity = result

            # Check if session is expired
            if datetime.now() > session_expiry:
                logger.info(
                    f"Session expired for user {username}: {session_id[:8]}...")
                self._deactivate_session(session_id)
                return None

            # Update last activity
            self._update_last_activity(session_id)

            logger.debug(f"Session validated for user {username}")
            return {
                'username': username,
                'email': email,
                'role': role,
                'session_id': session_id,
                'session_expiry': session_expiry.timestamp(),
                'device_info': device_info,
                'last_activity': last_activity
            }

        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None

    def _update_last_activity(self, session_id: str) -> None:
        """Update last activity timestamp for session."""
        try:
            query = """
                UPDATE cloud_user_sessions 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = %s
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (session_id,))
            self.conn.commit()
            cursor.close()

        except Exception as e:
            logger.error(f"Error updating last activity: {e}")

    def _deactivate_session(self, session_id: str) -> None:
        """Deactivate a session."""
        try:
            query = """
                UPDATE cloud_user_sessions 
                SET is_active = FALSE 
                WHERE session_id = %s
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (session_id,))
            self.conn.commit()
            cursor.close()

        except Exception as e:
            logger.error(f"Error deactivating session: {e}")

    def end_session(self, session_id: str) -> bool:
        """
        End a session (logout).

        Args:
            session_id: Session ID to end

        Returns:
            bool: True if successful
        """
        try:
            self._deactivate_session(session_id)
            logger.info(f"Session ended: {session_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False

    def end_user_sessions(self, username: str) -> bool:
        """
        End all sessions for a user.

        Args:
            username: Username to end sessions for

        Returns:
            bool: True if successful
        """
        try:
            query = """
                UPDATE cloud_user_sessions 
                SET is_active = FALSE 
                WHERE username = %s AND is_active = TRUE
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (username,))
            affected_rows = cursor.rowcount
            self.conn.commit()
            cursor.close()

            logger.info(f"Ended {affected_rows} sessions for user {username}")
            return True

        except Exception as e:
            logger.error(f"Error ending user sessions: {e}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            query = """
                DELETE FROM cloud_user_sessions 
                WHERE session_expiry < CURRENT_TIMESTAMP OR is_active = FALSE
            """

            cursor = self.conn.cursor()
            cursor.execute(query)
            deleted_count = cursor.rowcount
            self.conn.commit()
            cursor.close()

            logger.info(f"Cleaned up {deleted_count} expired sessions")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0

    def get_active_sessions(self, username: str) -> int:
        """
        Get count of active sessions for a user.

        Args:
            username: Username to check

        Returns:
            int: Number of active sessions
        """
        try:
            query = """
                SELECT COUNT(*) FROM cloud_user_sessions 
                WHERE username = %s AND is_active = TRUE AND session_expiry > CURRENT_TIMESTAMP
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (username,))
            count = cursor.fetchone()[0]
            cursor.close()

            return count

        except Exception as e:
            logger.error(f"Error getting active sessions count: {e}")
            return 0

    def extend_session(self, session_id: str, hours: int = 7) -> bool:
        """
        Extend session expiry time.

        Args:
            session_id: Session ID to extend
            hours: Hours to extend by

        Returns:
            bool: True if successful
        """
        try:
            new_expiry = datetime.now() + timedelta(hours=hours)

            query = """
                UPDATE cloud_user_sessions 
                SET session_expiry = %s 
                WHERE session_id = %s AND is_active = TRUE
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (new_expiry, session_id))
            affected_rows = cursor.rowcount
            self.conn.commit()
            cursor.close()

            if affected_rows > 0:
                logger.info(f"Session extended: {session_id[:8]}...")
                return True
            else:
                logger.warning(
                    f"Session not found for extension: {session_id[:8]}...")
                return False

        except Exception as e:
            logger.error(f"Error extending session: {e}")
            return False

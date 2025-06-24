"""User authentication and management service for the application."""

import random
import string
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import streamlit as st
from firebase_admin import exceptions, auth as firebase_auth
import requests
import re
import dns.resolver

from core.utils.cookies import get_cloud_cookie_manager, clear_user_cookie, save_user_to_cookie

# Session configuration
SESSION_TIMEOUT_HOURS = 7  # 7 hours session timeout
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class UserServiceError(Exception):
    """Custom exception for user service errors."""
    pass


class UserService:
    """
    Service for managing user authentication and operations.

    This service handles:
    - User login and logout
    - User registration and verification
    - Password validation
    - Session management
    - Activity logging
    """

    def __init__(self, firestore, auth, firebase_api, email_service):
        """
        Initialize UserService with required dependencies.

        Args:
            firestore: Firestore client
            auth: Firebase Auth client
            firebase_api: Firebase API key
            email_service: Email service instance
        """
        self.fs = firestore
        self.auth = auth
        self.firebase_api = firebase_api
        self.email_service = email_service

    def _validate_login_input(self, email: str, password: str) -> None:
        """Validate login input parameters."""
        if not email or not email.strip():
            raise ValidationError("Email is required")

        if not password or not password.strip():
            raise ValidationError("Password is required")

        # Email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Invalid email format")

    def _validate_signup_input(self, username: str, email: str, password: str, confirm_password: str) -> None:
        """Validate signup input parameters."""
        if not username or not username.strip():
            raise ValidationError("Username is required")

        if not email or not email.strip():
            raise ValidationError("Email is required")

        if not password or not password.strip():
            raise ValidationError("Password is required")

        if password != confirm_password:
            raise ValidationError("Passwords do not match")

        # Email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            # Password validation
            raise ValidationError("Invalid email format")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")

        # Additional password validation
        if len(password) > 30:
            # Optional: Check for password strength
            raise ValidationError("Password must be less than 128 characters")
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            raise ValidationError(
                "Password must contain at least one uppercase letter, one lowercase letter, and one number")

    def _handle_session_persistence(self, username: str, email: str, role: str) -> bool:
        """
        Handle session persistence using available storage methods.

        Args:
            username: User's username
            email: User's email
            role: User's role

        Returns:
            bool: True if at least one storage method succeeded
        """
        session_saved = False

        # Try persistent Firestore session first
        if "persistent_session_service" in st.session_state and st.session_state.persistent_session_service:
            try:
                persistent_service = st.session_state.persistent_session_service
                session_token = persistent_service.save_session(username, {
                    'username': username,
                    'useremail': email,
                    'role': role,
                    'logged_in': True,
                    'signout': False
                })
                if session_token:
                    session_saved = True
                    logger.info(
                        f"✅ Persistent session saved for user: {username}")
                else:
                    logger.warning("Failed to save persistent session")
            except Exception as e:
                logger.error(f"Failed to save persistent session: {e}")

        # Try cookie manager
        if not session_saved:
            try:
                cookie_manager = get_cloud_cookie_manager()
                if cookie_manager.save_user_session(username, email, role):
                    session_saved = True
                    logger.info(f"✅ Cookie session saved for user: {username}")
            except Exception as e:
                logger.debug(f"Cookie manager save failed: {e}")

        # Final fallback: session state only
        if not session_saved:
            logger.warning(
                "All session storage methods failed, using session state only")
            # Session state is already set in cookie manager or above

        return session_saved

    def _clear_all_sessions(self, username: str) -> None:
        """
        Clear all session data from available storage methods.
          Args:
            username: Username for logging purposes
        """
        # Clear persistent Firestore session
        if "persistent_session_service" in st.session_state and st.session_state.persistent_session_service:
            try:
                persistent_service = st.session_state.persistent_session_service
                persistent_service.clear_session(username)
                logger.info(
                    f"✅ Persistent session cleared for user: {username}")
            except Exception as e:
                logger.error(f"Failed to clear persistent session: {e}")

        # Clear cookies and session state
        try:
            clear_user_cookie()
            logger.info("Session cleared via cookie manager")
        except Exception as e:
            logger.debug(f"Cookie clearing failed: {e}")

    def _create_session(self, user, user_data: Dict[str, Any]) -> None:
        """Create user session using cloud-optimized storage and persistent Firestore session."""
        try:
            username = user_data.get('username', user.uid)
            email = user.email
            role = user_data['role']

            # Handle session persistence using helper method
            session_saved = self._handle_session_persistence(
                username, email, role)

            # Store user_uid for logout logging
            st.session_state.user_uid = user.uid

            # Ensure session_expiry is set in session_state
            current_time = time.time()
            session_expiry = current_time + SESSION_TIMEOUT_SECONDS
            st.session_state.session_expiry = session_expiry
            logger.info(
                f"🕒 Session expiry set to: {session_expiry} (current: {current_time}, timeout: {SESSION_TIMEOUT_HOURS}h)")

            if session_saved:
                logger.info(
                    f"Session created successfully for user: {username}")
            else:
                logger.warning("Session created with session state only")

            # Log activity
            self.save_login_logout(user.uid, "login")

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise UserServiceError(f"Session creation failed: {e}")
            raise UserServiceError(f"Session creation failed: {e}")

    def login(self, email: str, password: str) -> None:
        """
        Authenticate user and create session.

        Args:
            email: User email address
            password: User password

        Raises:
            ValidationError: If input validation fails
            AuthenticationError: If authentication fails
        """
        try:
            # Verify password through Firebase REST API
            self._validate_login_input(email, password)
            user_data = self.verify_password(email, password)
            if not user_data:
                st.warning("Invalid email or password")
                return

            user = self.auth.get_user_by_email(email)

            # Validate user in Firestore
            user_doc = self.fs.collection('users').document(user.uid).get()
            if not user_doc.exists:
                st.warning("User data not found.")
                return

            user_doc_data = user_doc.to_dict()

            # Check email verification status from Firestore (our custom OTP verification)
            if not user_doc_data.get("email_verified", False):
                st.warning(
                    "Your email is not verified. Please check your email and verify your account.")
                return            # Check if user is approved by admin
            # Check both 'verified' (boolean) and 'status' (string) fields for compatibility
            verified_field = user_doc_data.get("verified", False)
            status_field = str(user_doc_data.get("status", "")).strip()

            is_verified = (
                verified_field is True or
                status_field.lower() in ["verified", "approved", "active"]
            )

            logger.info(
                f"User verification check - Email: {email}, verified field: {verified_field}, status field: '{status_field}', is_verified: {is_verified}")

            if not is_verified:
                logger.warning(
                    f"User {email} login blocked - not verified. verified={verified_field}, status='{status_field}'")
                st.warning(
                    "Your account is pending admin approval. Please wait for verification.")
                return            # Create session after successful validation
            self._create_session(user, user_doc_data)

            st.success(
                f"Welcome back, {user_doc_data.get('username', user.uid)}!")

        except ValidationError as e:
            logger.warning(f"Login validation failed: {e}")
            st.warning(str(e))
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            st.warning(str(e))
        except Exception as e:
            logger.error(f"Login failed: {e}")
            st.error("An error occurred during login. Please try again.")

    def logout(self) -> None:
        """Log out the current user and clear session."""
        try:
            username = st.session_state.get("username", "")
            user_uid = st.session_state.get("user_uid", "")

            # Clear all sessions using helper method
            self._clear_all_sessions(username)

            # Log logout activity
            if user_uid:
                self.save_login_logout(user_uid, "logout")

            logger.info(f"User {username} logged out successfully")
            st.success("You have been logged out successfully")

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            # Force clear session state even if other operations fail
            clear_user_cookie()
            st.warning("Logout completed with some issues")

    def verify_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify user password using Firebase REST API.

        Args:
            email: User email
            password: User password

        Returns:
            User data if verification successful, None otherwise
        """
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_api}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }

            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                user_uid = data.get("localId")

                # Get user data from Firestore
                user_doc = self.fs.collection('users').document(user_uid).get()
                if user_doc.exists:
                    return user_doc.to_dict()

            return None

        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return None

    def save_login_logout(self, user_uid: str, action: str) -> None:
        """
        Save login/logout activity to Firestore.

        Args:
            user_uid: User UID
            action: 'login' or 'logout'
        """
        try:
            activity_data = {
                "user_uid": user_uid,
                "action": action,
                "timestamp": datetime.now(),
                "ip_address": self._get_client_ip()
            }

            self.fs.collection('user_activities').add(activity_data)
            logger.info(
                f"{action.capitalize()} activity saved for user {user_uid}")

        except Exception as e:
            logger.error(f"Failed to save {action} activity: {e}")

    def _get_client_ip(self) -> str:
        """Get client IP address."""
        try:
            # In Streamlit Cloud, this might not work as expected
            # You might need to use headers like X-Forwarded-For
            return "Unknown"
        except Exception:
            return "Unknown"

    def signup(self, username: str, email: str, password: str, confirm_password: str) -> None:
        """
        Register a new user.

        Args:
            username: Desired username
            email: User email address
            password: User password
            confirm_password: Password confirmation

        Raises:
            ValidationError: If input validation fails
        """
        try:
            self._validate_signup_input(
                username, email, password, confirm_password)

            # Create user in Firebase Auth
            user = self.auth.create_user(
                email=email,
                password=password,
                display_name=username
            )

            # Create user document in Firestore
            user_data = {
                'username': username,
                'email': email,
                'role': 'employee',  # Default role
                'email_verified': False,
                'verified': False,  # Admin approval required
                'created_at': datetime.now(),
                'otp_code': self._generate_otp_code(),
                'otp_expires_at': datetime.now() + timedelta(minutes=10)
            }

            self.fs.collection('users').document(user.uid).set(user_data)

            # Send verification email
            if self.email_service:
                self.email_service.send_verification_email(
                    email, user_data['otp_code'])

            st.success(
                "Registration successful! Please check your email for verification code.")
            logger.info(f"User registered successfully: {username} ({email})")

        except ValidationError as e:
            logger.warning(f"Signup validation failed: {e}")
            st.warning(str(e))
        except exceptions.FirebaseError as e:
            logger.error(f"Firebase error during signup: {e}")
            if "EMAIL_EXISTS" in str(e):
                st.warning(
                    "Email already exists. Please use a different email.")
            else:
                st.error("Registration failed. Please try again.")
        except Exception as e:
            logger.error(f"Signup failed: {e}")
            st.error("An error occurred during registration. Please try again.")

    def _generate_otp_code(self) -> str:
        """Generate a 6-digit OTP code."""
        return ''.join(random.choices(string.digits, k=6))

    def verify_otp(self, email: str, otp_code: str) -> bool:
        """
        Verify OTP code for email verification.

        Args:
            email: User email
            otp_code: OTP code to verify

        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Find user by email
            users = self.fs.collection('users').where(
                'email', '==', email).get()

            if not users:
                st.warning("User not found.")
                return False

            user_doc = users[0]
            user_data = user_doc.to_dict()

            # Check OTP validity
            if user_data.get('otp_code') != otp_code:
                st.warning("Invalid OTP code.")
                return False

            if datetime.now() > user_data.get('otp_expires_at'):
                st.warning("OTP code has expired. Please request a new one.")
                return False

            # Mark email as verified
            user_doc.reference.update({
                'email_verified': True,
                'otp_code': None,
                'otp_expires_at': None
            })

            st.success(
                "Email verified successfully! Please wait for admin approval.")
            logger.info(f"Email verified for user: {email}")
            return True

        except Exception as e:
            logger.error(f"OTP verification failed: {e}")
            st.error("Verification failed. Please try again.")
            return False

    def resend_otp(self, email: str) -> None:
        """
        Resend OTP code to user email.

        Args:
            email: User email
        """
        try:
            # Find user by email
            users = self.fs.collection('users').where(
                'email', '==', email).get()

            if not users:
                st.warning("User not found.")
                return

            user_doc = users[0]

            # Generate new OTP
            new_otp = self._generate_otp_code()

            # Update user document
            user_doc.reference.update({
                'otp_code': new_otp,
                'otp_expires_at': datetime.now() + timedelta(minutes=10)
            })

            # Send new OTP
            if self.email_service:
                self.email_service.send_verification_email(email, new_otp)

            st.success("New OTP code sent to your email.")
            logger.info(f"OTP resent for user: {email}")

        except Exception as e:
            logger.error(f"Failed to resend OTP: {e}")
            st.error("Failed to resend OTP. Please try again.")

    def reset_password_request(self, email: str) -> None:
        """
        Send password reset email.

        Args:
            email: User email
        """
        try:
            self.auth.generate_password_reset_link(email)
            st.success("Password reset email sent. Please check your inbox.")
            logger.info(f"Password reset requested for: {email}")

        except exceptions.FirebaseError as e:
            logger.error(f"Password reset failed: {e}")
            if "USER_NOT_FOUND" in str(e):
                st.warning("Email not found.")
            else:
                st.error("Failed to send password reset email.")
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            st.error("An error occurred. Please try again.")

    def restore_user_session(self) -> bool:
        """
        Restore user session from persistent storage with enhanced cloud support.
        This method is called during app initialization to recover user sessions.

        Returns:
            bool: True if session was successfully restored, False otherwise
        """
        try:
            # Check if we already have a valid session
            current_user = st.session_state.get("username", "")
            current_signout = st.session_state.get("signout", True)
            current_expiry = st.session_state.get("session_expiry", 0)

            # If we already have a valid, non-expired session, no need to restore
            if (current_user and not current_signout and current_expiry > 0 and current_expiry > time.time()):
                logger.debug(
                    f"Valid session already exists for: {current_user}")
                return True

            logger.debug(
                "Attempting to restore user session from persistent storage...")

            # Strategy 1: Try cookie manager (primary method for this app)
            try:
                cookie_manager = get_cloud_cookie_manager()
                if cookie_manager.load_user_session():
                    restored_user = st.session_state.get("username", "")
                    if restored_user:
                        logger.info(
                            f"Session restored from cookies: {restored_user}")
                        return True
            except Exception as e:
                logger.debug(f"Cookie restoration failed: {e}")

            # Strategy 2: Check for any persisted session data in session_state
            try:
                for key in st.session_state.keys():
                    if key.startswith("_encoded_session_"):
                        encoded_data = st.session_state[key]
                        if encoded_data:
                            import json
                            session_data = json.loads(encoded_data)

                            # Validate session is not expired
                            session_expiry = session_data.get(
                                "session_expiry", 0)
                            if session_expiry > time.time():
                                # Restore session data
                                st.session_state.username = session_data.get(
                                    "username", "")
                                st.session_state.useremail = session_data.get(
                                    "email", "")
                                st.session_state.role = session_data.get(
                                    "role", "")
                                st.session_state.signout = session_data.get(
                                    "signout", True)
                                st.session_state.login_timestamp = session_data.get(
                                    "login_timestamp", time.time())
                                st.session_state.session_expiry = session_expiry

                                restored_user = st.session_state.get(
                                    "username", "")
                                if restored_user:
                                    logger.info(
                                        f"Session restored from encoded data: {restored_user}")
                                    return True
                            else:
                                # Clean up expired encoded session
                                del st.session_state[key]
            except Exception as e:
                logger.debug(f"Encoded session restoration failed: {e}")

            # No valid session found
            logger.debug("No valid session found to restore")
            return False

        except Exception as e:
            logger.error(f"Failed to restore user session: {e}")
            return False

    def is_session_valid(self) -> bool:
        """
        Check if the current user session is valid and not expired.

        Returns:
            bool: True if session is valid, False otherwise
        """
        try:
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)

            # Basic checks
            if not username or signout:
                logger.info("❌ Session invalid - no username or signed out")
                return False

            # Check session expiry using helper
            time_info = self._get_session_remaining_time()

            if time_info.get("expired", True):
                logger.info(f"❌ Session expired for user: {username}")
                # Auto-clear expired session
                clear_user_cookie()
                return False

            logger.info(
                f"✅ Session valid for: {username} ({time_info.get('remaining_hours', 0):.1f}h remaining)")
            return True

        except Exception as e:
            logger.error(f"Failed to validate session: {e}")
            return False

    def is_user_authenticated(self) -> bool:
        """
        Check if user is currently authenticated with valid session.

        Returns:
            bool: True if user is authenticated, False otherwise
        """
        try:
            # Quick check of session state
            username = st.session_state.get("username", "")
            signout = st.session_state.get("signout", True)

            if not username or signout:
                return False

            # Validate session is still valid
            return self.is_session_valid()

        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user information.

        Returns:
            Dict with user info if authenticated, None otherwise
        """
        try:
            if not self.is_user_authenticated():
                return None

            return {
                "username": st.session_state.get("username", ""),
                "email": st.session_state.get("useremail", ""),
                "role": st.session_state.get("role", ""),
                "login_timestamp": st.session_state.get("login_timestamp"),
                "session_expiry": st.session_state.get("session_expiry")
            }

        except Exception as e:
            logger.error(f"Failed to get current user: {e}")
            return None

    def refresh_session(self) -> bool:
        """
        Refresh current session to extend expiry time (cookies only).

        Returns:
            bool: True if session refreshed successfully
        """
        try:
            if not self.is_user_authenticated():
                return False

            username = st.session_state.get("username", "")
            email = st.session_state.get("useremail", "")
            role = st.session_state.get("role", "")

            # Refresh session by saving to cookies again (extends 7-hour timeout)
            cookie_saved = save_user_to_cookie(username, email, role)

            if cookie_saved:
                logger.info(f"Session refreshed for user: {username}")
                return True
            else:
                logger.warning(
                    f"Failed to refresh session for user: {username}")
                return False

        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            return False

    def logout_if_expired(self) -> None:
        """
        Log out user if session has expired.
        """
        try:
            if not self.is_session_valid():
                logger.info("Session expired, logging out user")
                self.logout()
        except Exception as e:
            logger.error(f"Error checking session expiry: {e}")

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current session information.

        Returns:
            Dict with session info if valid, None otherwise
        """
        try:
            if not self.is_user_authenticated():
                return None

            # Get time information using helper
            time_info = self._get_session_remaining_time()

            return {
                "username": st.session_state.get("username", ""),
                "email": st.session_state.get("useremail", ""),
                "role": st.session_state.get("role", ""),
                "login_timestamp": st.session_state.get("login_timestamp"),
                "session_expiry": time_info.get("expiry_timestamp"),
                "remaining_time_seconds": time_info.get("remaining_seconds", 0),
                "remaining_hours": time_info.get("remaining_hours", 0),
                "remaining_minutes": time_info.get("remaining_minutes", 0),
                "is_valid": time_info.get("valid", False)
            }

        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return None

    def send_verification_otp(self, email: str) -> tuple[bool, str]:
        """
        Send verification OTP to email.

        Args:
            email: User email address

        Returns:
            Tuple of (success, message)
        """
        try:
            # Find user by email
            users = self.fs.collection('users').where(
                'email', '==', email).get()

            if not users:
                return False, "User not found."

            user_doc = users[0]
            user_data = user_doc.to_dict()

            # Check if email is already verified
            if user_data.get('email_verified', False):
                return False, "Email is already verified."

            # Generate new OTP
            new_otp = self._generate_otp_code()

            # Update user document
            user_doc.reference.update({
                'otp_code': new_otp,
                'otp_expires_at': datetime.now() + timedelta(minutes=10)
            })

            # Send OTP via email
            if self.email_service:
                try:
                    self.email_service.send_verification_email(email, new_otp)
                    logger.info(f"Verification OTP sent to: {email}")
                    return True, "Verification code sent to your email."
                except Exception as e:
                    logger.error(f"Failed to send verification email: {e}")
                    return False, "Failed to send verification email."
            else:
                logger.warning("Email service not available")
                return False, "Email service not available."

        except Exception as e:
            logger.error(f"Failed to send verification OTP: {e}")
            return False, "An error occurred while sending verification code."

    def complete_registration_after_otp(self, email: str, otp_code: str) -> None:
        """
        Complete user registration after OTP verification with UI feedback.

        Args:
            email: User email address
            otp_code: OTP verification code
        """
        try:
            if not email or not otp_code:
                st.warning("⚠️ Email dan kode verifikasi harus diisi!")
                return

            if len(otp_code) != 6 or not otp_code.isdigit():
                st.error("❌ Kode verifikasi harus 6 digit angka!")
                return

            # Verify OTP
            success = self.verify_otp(email, otp_code)

            if success:
                # Clear OTP verification state
                if 'show_otp_verification' in st.session_state:
                    del st.session_state['show_otp_verification']
                if 'verification_email' in st.session_state:
                    del st.session_state['verification_email']
                if 'pending_registration' in st.session_state and email in st.session_state.pending_registration:
                    del st.session_state.pending_registration[email]

                st.success(
                    "✅ Email berhasil diverifikasi! Akun Anda menunggu persetujuan admin.")
                st.info(
                    "💡 Anda akan mendapat notifikasi email setelah akun disetujui admin.")

                # Force rerun to show updated UI
                time.sleep(2)
                st.rerun()

        except Exception as e:
            logger.error(f"Error during OTP completion: {e}")
            st.error("❌ Terjadi kesalahan saat verifikasi. Silakan coba lagi.")

    def _is_session_expired(self, session_expiry: float) -> bool:
        """
        Check if a session timestamp is expired.

        Args:
            session_expiry: Session expiry timestamp

        Returns:
            bool: True if expired, False otherwise
        """
        try:
            current_time = time.time()
            return current_time > session_expiry
        except (ValueError, TypeError):
            return True

    def _normalize_session_expiry(self, session_expiry) -> float:
        """
        Normalize session expiry to Unix timestamp.

        Args:
            session_expiry: Session expiry in various formats

        Returns:
            float: Unix timestamp or 0 if invalid
        """
        try:
            if isinstance(session_expiry, str):
                # Handle ISO format string
                from datetime import datetime
                return datetime.fromisoformat(session_expiry.replace('Z', '+00:00')).timestamp()
            elif isinstance(session_expiry, (int, float)):
                return float(session_expiry)
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _get_session_remaining_time(self) -> Dict[str, Any]:
        """
        Get remaining session time information.

        Returns:
            Dict with remaining time details
        """
        try:
            session_expiry = st.session_state.get("session_expiry", 0)
            normalized_expiry = self._normalize_session_expiry(session_expiry)

            if normalized_expiry <= 0:
                return {"valid": False, "expired": True}

            current_time = time.time()
            remaining_seconds = max(0, normalized_expiry - current_time)
            remaining_minutes = remaining_seconds / 60
            remaining_hours = remaining_seconds / 3600

            return {
                "valid": remaining_seconds > 0,
                "expired": remaining_seconds <= 0,
                "remaining_seconds": remaining_seconds,
                "remaining_minutes": remaining_minutes,
                "remaining_hours": remaining_hours,
                "expiry_timestamp": normalized_expiry
            }
        except Exception as e:
            logger.error(f"Error calculating session time: {e}")
            return {"valid": False, "expired": True, "error": str(e)}

    def get_cookie_status(self) -> Dict[str, Any]:
        """
        Get cookie manager status information for debugging.

        Returns:
            Dict with cookie status information
        """
        try:
            cookie_manager = get_cloud_cookie_manager()

            return {
                "cookies_available": cookie_manager is not None,
                "cookies_ready": cookie_manager.ready if cookie_manager else False,
                "session_timeout_hours": SESSION_TIMEOUT_HOURS,
                "current_user": st.session_state.get("username", ""),
                "is_authenticated": self.is_user_authenticated(),
                "session_valid": self.is_session_valid() if self.is_user_authenticated() else False
            }

        except Exception as e:
            logger.error(f"Error getting cookie status: {e}")
            return {"error": str(e), "cookies_available": False}

    def debug_session_state(self) -> Dict[str, Any]:
        """
        Get session state information for debugging (non-sensitive data only).

        Returns:
            Dict with session state information
        """
        try:
            relevant_keys = [
                "username", "useremail", "role", "signout",
                "login_timestamp", "session_expiry", "user_uid"
            ]

            debug_info = {}
            for key in relevant_keys:
                if key in st.session_state:
                    value = st.session_state[key]
                    # Mask sensitive information
                    if key == "useremail" and value:
                        parts = value.split("@")
                        if len(parts) == 2:
                            value = f"{parts[0][:2]}***@{parts[1]}"
                    debug_info[key] = value

            # Add calculated values
            time_info = self._get_session_remaining_time()
            debug_info.update({
                "remaining_hours": time_info.get("remaining_hours", 0),
                "session_expired": time_info.get("expired", True),
                "session_valid": time_info.get("valid", False)
            })

            return debug_info

        except Exception as e:
            logger.error(f"Error getting debug info: {e}")
            return {"error": str(e)}

    # ...existing methods...

"""User authentication and management service for the application."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import streamlit as st
from firebase_admin import exceptions
import requests
import re
import dns.resolver
import time

from core.utils.cookies import save_user_to_cookie, clear_user_cookie

# Session configuration
SESSION_TIMEOUT_HOURS = 7  # 7 hours session timeout
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600

# Configure logging
logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    """Custom exception for user service errors."""
    pass


class ValidationError(UserServiceError):
    """Exception raised for validation errors."""
    pass


class AuthenticationError(UserServiceError):
    """Exception raised for authentication errors."""
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
        if not email or not password:
            raise ValidationError("Email and password are required")

        # Basic email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Invalid email format")

        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")

    def _validate_signup_input(self, username: str, email: str, password: str, confirm_password: str) -> None:
        """Validate signup input parameters."""
        if not all([username, email, password, confirm_password]):
            raise ValidationError("All fields are required")

        if password != confirm_password:
            raise ValidationError("Passwords do not match")

        # Username validation
        if len(username) < 3 or len(username) > 30:
            raise ValidationError("Username must be 3-30 characters")

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError(
                "Username can only contain letters, numbers, and underscores")

        # Email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Invalid email format")

        # Password validation
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

    def _create_session(self, user, user_data: Dict[str, Any]) -> None:
        """Create user session after successful authentication."""
        try:
            username = user_data.get('username', user.uid)
            email = user.email
            role = user_data['role']

            # Create login timestamp for session timeout
            login_timestamp = time.time()
            session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS

            # Set session state with timeout information
            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False
            st.session_state.login_timestamp = login_timestamp
            st.session_state.session_expiry = session_expiry

            logger.info(
                f"Session state set - username: {username}, role: {role}, signout: False, expires: {datetime.fromtimestamp(session_expiry)}")

            # Save to cookies (legacy support) with timestamp
            cookie_saved = self._save_user_to_cookie_with_timestamp(
                username, email, role, login_timestamp)
            if not cookie_saved:
                # Save to cloud session storage (primary) with timestamp
                logger.warning("Failed to save user data to cookies")
            try:
                cloud_session_storage = st.session_state.get(
                    "cloud_session_storage")
                if cloud_session_storage:
                    session_saved = cloud_session_storage.save_session(
                        username, email, role,
                        login_timestamp=login_timestamp,
                        session_expiry=session_expiry)
                    if session_saved:
                        logger.info(
                            "User session saved to cloud session storage")
                    else:
                        logger.warning(
                            "Failed to save to cloud session storage")
                else:
                    logger.warning("Cloud session storage not available")
            except Exception as e:
                logger.error(f"Error saving to cloud session storage: {e}")

            # Save to legacy session storage (fallback)
            try:
                session_storage_service = st.session_state.get(
                    "session_storage_service")
                if session_storage_service:
                    session_saved = session_storage_service.save_user_session(
                        username, email, role)
                    if session_saved:
                        logger.info(
                            "User session saved to legacy session storage service")
                    else:
                        logger.warning(
                            "Failed to save to legacy session storage service")
                else:
                    logger.warning(
                        "Legacy session storage service not available")
            except Exception as e:
                logger.error(
                    f"Error saving to legacy session storage service: {e}")

            # Log activity
            self.save_login_logout(user.uid, "login")

            logger.info(f"Session created successfully for user: {username}")

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
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
            self._validate_login_input(email, password)

            # Verify password through Firebase REST API
            user_data = self.verify_password(email, password)
            if not user_data:
                st.warning("Invalid email or password")
                return

            user = self.auth.get_user_by_email(email)
            if not user.email_verified:
                st.warning("Email not verified. Please check your inbox.")
                return

            # Validate user in Firestore
            user_doc = self.fs.collection('users').document(user.uid).get()
            if not user_doc.exists:
                st.warning("User data not found.")
                return

            user_doc_data = user_doc.to_dict()
            if user_doc_data.get("status") != "Verified":
                st.warning("Your account is not verified by admin yet.")
                return

            # User is verified, create session and login
            self._create_session(user, user_doc_data)
            st.success(f"Login successful as {user_doc_data['role']}!")
        except ValidationError as e:
            st.warning(str(e))
        except exceptions.FirebaseError as e:
            logger.error(f"Firebase error during login: {e}")
            st.warning(f"A Firebase error occurred: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            st.error(f"An unexpected error occurred: {e}")

    def logout(self) -> None:
        """
        Log out the current user and clean up session data.

        Raises:
            UserServiceError: If logout process fails
        """
        try:
            username = st.session_state.get('username', '')
            if username:
                self.save_login_logout(username, "logout")

            # Clear legacy cookies
            clear_user_cookie()

            # Clear cloud session storage (primary)
            try:
                cloud_session_storage = st.session_state.get(
                    "cloud_session_storage")
                if cloud_session_storage:
                    session_cleared = cloud_session_storage.clear_session(
                        username)
                    if session_cleared:
                        logger.info(
                            "User session cleared from cloud session storage")
                    else:
                        logger.warning("Failed to clear cloud session storage")
                else:
                    logger.warning(
                        "Cloud session storage not available for logout")
            except Exception as e:
                logger.error(f"Error clearing cloud session storage: {e}")

            # Clear legacy session storage service (fallback)
            try:
                session_storage_service = st.session_state.get(
                    "session_storage_service")
                if session_storage_service:
                    session_cleared = session_storage_service.clear_user_session(
                        username)
                    if session_cleared:
                        logger.info(
                            "User session cleared from legacy session storage service")
                    else:
                        logger.warning(
                            "Failed to clear legacy session storage service")
                else:
                    logger.warning(
                        "Legacy session storage service not available for logout")
            except Exception as e:
                logger.error(
                    f"Error clearing legacy session storage service: {e}")

            # Clear session state
            st.session_state.signout = True
            st.session_state.username = ''
            st.session_state.useremail = ''
            st.session_state.role = ''

            logger.info("User logged out successfully")

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            raise UserServiceError(f"Logout failed: {e}")

    def _save_user_to_cookie_with_timestamp(self, username: str, email: str, role: str, login_timestamp: float) -> bool:
        """Save user to cookie with login timestamp for session timeout."""
        try:
            # Use the existing cookie function but with additional timestamp handling
            success = save_user_to_cookie(username, email, role)
            if success and hasattr(st.session_state, 'cookies') and st.session_state.cookies:
                # Also save timestamp to cookies if available
                try:
                    cookies = st.session_state.cookies
                    cookies["login_timestamp"] = str(login_timestamp)
                    cookies["session_expiry"] = str(
                        login_timestamp + SESSION_TIMEOUT_SECONDS)
                    cookies.save()
                except Exception as e:
                    logger.warning(f"Could not save timestamp to cookies: {e}")
            return success
        except Exception as e:
            logger.error(f"Error saving user with timestamp: {e}")
            return False

    def is_session_valid(self) -> bool:
        """
        Check if current session is valid (not expired).

        Returns:
            bool: True if session is valid, False if expired or invalid
        """
        try:
            # Check if user is logged in
            if st.session_state.get('signout', True):
                return False

            if not st.session_state.get('username'):
                return False

            # Check session expiry
            current_time = time.time()
            session_expiry = st.session_state.get('session_expiry')

            if session_expiry is None:
                # No expiry set - check login timestamp
                login_timestamp = st.session_state.get('login_timestamp')
                if login_timestamp is None:
                    logger.warning(
                        "No session timestamps found - session invalid")
                    return False

                # Calculate expiry from login timestamp
                session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS
                st.session_state.session_expiry = session_expiry

            if current_time > session_expiry:
                logger.info(
                    f"Session expired for user {st.session_state.get('username')} at {datetime.fromtimestamp(session_expiry)}")
                return False

            # Session is still valid
            remaining_time = session_expiry - current_time
            logger.debug(
                f"Session valid for {st.session_state.get('username')}, {remaining_time/3600:.1f} hours remaining")
            return True

        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about current session including time remaining.

        Returns:
            Dict containing session information
        """
        try:
            if not self.is_session_valid():
                return {
                    'is_valid': False,
                    'message': 'Session expired or invalid'
                }

            current_time = time.time()
            session_expiry = st.session_state.get('session_expiry')
            login_timestamp = st.session_state.get('login_timestamp')

            if session_expiry and login_timestamp:
                remaining_seconds = session_expiry - current_time
                remaining_hours = remaining_seconds / 3600

                login_time = datetime.fromtimestamp(login_timestamp)
                expiry_time = datetime.fromtimestamp(session_expiry)

                return {
                    'is_valid': True,
                    'username': st.session_state.get('username'),
                    'login_time': login_time,
                    'expiry_time': expiry_time,
                    'remaining_hours': remaining_hours,
                    'remaining_minutes': remaining_seconds / 60,
                    'session_timeout_hours': SESSION_TIMEOUT_HOURS
                }
            else:
                return {
                    'is_valid': False,
                    'message': 'Session timing information not available'
                }

        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {
                'is_valid': False,
                'message': f'Error retrieving session info: {e}'
            }

    def logout_if_expired(self) -> bool:
        """
        Check if session is expired and logout if needed.

        Returns:
            bool: True if session was expired and logout performed, False otherwise
        """
        try:
            if not self.is_session_valid():
                username = st.session_state.get('username', 'Unknown')
                logger.info(
                    f"Session expired for user {username}, logging out")

                # Show expiry message before logout
                st.warning(
                    f"⏰ Sesi Anda telah berakhir setelah {SESSION_TIMEOUT_HOURS} jam. Silakan login kembali.")

                # Perform logout
                self.logout()
                return True
            return False

        except Exception as e:
            logger.error(f"Error during session expiry check: {e}")
            return False

    def signup(self, username: str, email: str, password: str, confirm_password: str, role: str) -> None:
        """
        Register a new user account with OTP verification.
        Note: Input validation should be done before calling this method.

        Args:
            username: Unique username
            email: User email address
            password: User password
            confirm_password: Password confirmation
            role: User role

        Raises:
            ValidationError: If input validation fails
            AuthenticationError: If user already exists
        """
        try:
            self._validate_signup_input(
                username, email, password, confirm_password)

            # Check if username already exists in Firestore
            existing_users = self.fs.collection('users').where(
                'username', '==', username).limit(1).get()
            if existing_users:
                st.warning("Username already taken. Please choose another.")
                return

            # Check if email already exists in Firebase Auth
            try:
                existing_user = self.auth.get_user_by_email(email)
                if existing_user:
                    st.warning(
                        "Email already registered. Please use a different email or try logging in.")
                    return
            except exceptions.UserNotFoundError:
                # This is good - email doesn't exist yet
                pass

            # Generate and send OTP
            success, otp_message = self.send_verification_otp(email)

            if not success:
                st.error(otp_message)
                return

            # Store registration data in session for later completion
            if 'pending_registration' not in st.session_state:
                st.session_state.pending_registration = {}

            # Debug: Log what we're storing
            logger.info(
                f"Storing registration data - Username: {username}, Email: {email}, Password length: {len(password)}")

            st.session_state.pending_registration[email] = {
                'username': username,
                'password': password,
                'role': role,
                'timestamp': datetime.now()
            }

            # Debug: Verify what was stored
            stored_data = st.session_state.pending_registration[email]
            logger.info(
                f"Verified stored data - Password length: {len(stored_data.get('password', ''))}")

            st.success(otp_message)

            # Set flag to show OTP verification form
            st.session_state.show_otp_verification = True
            st.session_state.verification_email = email

        except ValidationError as e:
            st.warning(str(e))
        except exceptions.AlreadyExistsError:
            st.warning("Email or username already taken.")
        except Exception as e:
            logger.error(f"Error during signup: {e}")
            st.error(f"An error occurred: {e}")

    def complete_registration_after_otp(self, email: str, otp: str) -> None:
        """
        Complete user registration after OTP verification.

        Args:
            email: User email address
            otp: OTP code entered by user
        """
        try:
            # Verify OTP first
            is_verified, message = self.verify_email_otp(email, otp)

            if not is_verified:
                st.error(message)
                return

            # Get stored registration data
            if 'pending_registration' not in st.session_state or email not in st.session_state.pending_registration:
                st.error(
                    "Registration data not found. Please try registering again.")
                return

            registration_data = st.session_state.pending_registration[email]
            username = registration_data['username']
            password = registration_data['password']
            role = registration_data['role']

            # Debug: Log what we're retrieving
            logger.info(
                f"Retrieving registration data - Username: {username}, Password length: {len(password)}")

            # Check registration data age (max 30 minutes)
            registration_time = registration_data.get('timestamp')
            if registration_time and (datetime.now() - registration_time).total_seconds() > 1800:
                st.error("Registration session expired. Please try again.")
                del st.session_state.pending_registration[email]
                return

            # Save user data to Firestore
            self.auth.create_user(email=email, password=password, uid=username)
            user_ref = self.fs.collection("users").document(username)
            user_data = {
                "username": username,
                "email": email,
                "role": role,
                "status": "Pending",  # Still needs admin verification
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "email_verified": True,  # Email verified via OTP
                "otp_verified_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            user_ref.set(user_data)

            # Clean up pending registration
            # Clean up verification UI state
            del st.session_state.pending_registration[email]
            if 'show_otp_verification' in st.session_state:
                del st.session_state.show_otp_verification
            if 'verification_email' in st.session_state:
                del st.session_state.verification_email

            st.success(
                "Account created successfully! Your account is pending admin verification.")

            logger.info(f"User {username} registered successfully")

        except exceptions.AlreadyExistsError:
            st.error("User already exists.")
        except Exception as e:
            logger.error(f"Error completing registration: {e}")
            st.error(f"Terjadi error saat menyelesaikan pendaftaran: {e}")

    def verify_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify user password using Firebase REST API.

        Args:
            email: User email address
            password: User password

        Returns:
            User data if verification successful, None otherwise

        Raises:
            AuthenticationError: If verification fails
        """
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_api}"
            data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }

            response = requests.post(url, json=data)
            response_data = response.json()

            if response.status_code == 200:
                return response_data
            else:
                error_message = response_data.get(
                    "error", {}).get("message", "Unknown error")
                logger.warning(
                    f"Password verification failed for {email}: {error_message}")
                return None

        except Exception as e:
            logger.error(f"Error verifying password for {email}: {e}")
            raise AuthenticationError(f"Password verification failed: {e}")

    def send_verification_otp(self, email: str) -> tuple[bool, str]:
        """
        Send OTP verification email to user.

        Args:
            email: User email address

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))

            # Store OTP in session with timestamp
            if 'otp_storage' not in st.session_state:
                st.session_state.otp_storage = {}

            st.session_state.otp_storage[email] = {
                'otp': otp,
                'timestamp': datetime.now()
            }

            # Send email
            subject = "Verification Code for ICONNET Account"
            body = f"""
            Hi there!

            Your verification code for ICONNET account registration is: {otp}

            This code will expire in 10 minutes.

            If you didn't request this code, please ignore this email.

            Best regards,
            ICONNET Team
            """

            success = self.email_service.send_email(email, subject, body)

            if success:
                return True, f"Verification code sent to {email}. Please check your inbox."
            else:
                return False, "Failed to send verification email. Please try again."

        except Exception as e:
            logger.error(f"Error sending OTP to {email}: {e}")
            return False, f"Error sending verification email: {e}"

    def verify_email_otp(self, email: str, user_otp: str) -> tuple[bool, str]:
        """
        Verify OTP code for email verification.

        Args:
            email: User email address
            user_otp: OTP code entered by user

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        try:
            if 'otp_storage' not in st.session_state or email not in st.session_state.otp_storage:
                return False, "No verification code found. Please request a new code."

            stored_data = st.session_state.otp_storage[email]
            stored_otp = stored_data['otp']
            timestamp = stored_data['timestamp']

            # Check if OTP is expired (10 minutes)
            if (datetime.now() - timestamp).total_seconds() > 600:
                del st.session_state.otp_storage[email]
                return False, "Verification code expired. Please request a new code."

            # Verify OTP
            if user_otp == stored_otp:
                # OTP is valid, remove it from storage
                del st.session_state.otp_storage[email]
                return True, "Email verified successfully!"
            else:
                return False, "Invalid verification code. Please try again."

        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {e}")
            return False, f"Error verifying code: {e}"

    def save_login_logout(self, username: str, action: str) -> None:
        """
        Log user login/logout activity.

        Args:
            username: User ID/username
            action: Either 'login' or 'logout'
        """
        try:
            activity_doc = {
                "username": username,
                "action": action,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address": "Unknown"  # Could be enhanced to get real IP
            }

            self.fs.collection("user_activity").add(activity_doc)
            logger.info(f"Activity logged: {username} - {action}")

        except Exception as e:
            logger.error(f"Failed to log activity for {username}: {e}")
            # Don't raise exception as this is not critical

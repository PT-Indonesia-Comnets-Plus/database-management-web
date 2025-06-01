"""User authentication and management service for the application."""

from datetime import datetime
from typing import Optional, Dict, Any
import logging
import streamlit as st
from firebase_admin import exceptions
import requests

from core.utils.cookies import save_user_to_cookie, clear_user_cookie

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
            firestore: Firestore database instance
            auth: Firebase Auth instance
            firebase_api: Firebase API utilities
            email_service: Email service for verification emails

        Raises:
            UserServiceError: If any required dependency is None
        """
        if not all([firestore, auth, firebase_api, email_service]):
            raise UserServiceError("All dependencies are required")

        self.fs = firestore
        self.auth = auth
        self.firebase_api = firebase_api
        self.email_service = email_service

    def _validate_login_input(self, email: str, password: str) -> None:
        """Validate login input parameters."""
        if not email or not email.strip():
            raise ValidationError("Email cannot be empty")
        if not password or not password.strip():
            raise ValidationError("Password cannot be empty")

    def _validate_signup_input(self, username: str, email: str, password: str, confirm_password: str) -> None:
        """Validate signup input parameters."""
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty")
        if not email or not email.strip():
            raise ValidationError("Email cannot be empty")
        if not password or not confirm_password:
            raise ValidationError("Password cannot be empty")
        if password != confirm_password:
            raise ValidationError("Passwords do not match")

    def _create_session(self, user, user_data: Dict[str, Any]) -> None:
        """Create user session after successful authentication."""
        try:
            st.session_state.username = user.uid
            st.session_state.useremail = user.email
            st.session_state.role = user_data['role']
            st.session_state.signout = False

            # Save to cookies with proper error handling
            cookie_saved = save_user_to_cookie(
                user.uid, user.email, user_data['role'])
            if not cookie_saved:
                logger.warning(
                    "Failed to save user data to cookies, but session created")

            # Log activity
            self.save_login_logout(user.uid, "login")

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

    def signup(self, username: str, email: str, password: str, confirm_password: str, role: str) -> None:
        """
        Register a new user account.

        Args:
            username: Unique username
            email: User email address
            password: User password
            confirm_password: Password confirmation
            role: User role

        Raises:
            ValidationError: If input validation fails
            UserServiceError: If user creation fails
        """
        try:
            self._validate_signup_input(
                username, email, password, confirm_password)

            user_ref = self.fs.collection("users").document(username)

            # Check if username is already taken
            if user_ref.get().exists:
                st.warning("Username already taken")
                return

            # Check if email is already taken
            try:
                self.auth.get_user_by_email(email)
                st.warning("Email already taken")
                return
            except exceptions.NotFoundError:
                pass

            # Create user in Firebase Authentication
            self.auth.create_user(email=email, password=password, uid=username)

            # Save user data to Firestore
            user_data = {
                "username": username,
                "email": email,
                "role": role,
                "status": "Pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            user_ref.set(user_data)

            # Send verification email
            user = self.auth.get_user_by_email(email)
            verification_link = self.auth.generate_email_verification_link(
                email)
            self.email_service.send_verification_email(
                email, user, verification_link)

            st.success(
                "Account created successfully! Please verify your email.")
            st.balloons()

            logger.info(f"User account created successfully: {email}")

        except ValidationError as e:
            st.warning(str(e))
        except exceptions.AlreadyExistsError:
            st.warning("Email or username already taken.")
        except Exception as e:
            logger.error(f"Error during signup: {e}")
            st.error(f"An error occurred: {e}")

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

            clear_user_cookie()
            st.session_state.signout = True
            st.session_state.username = ''
            st.session_state.useremail = ''
            st.session_state.role = ''

            logger.info("User logged out successfully")

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            raise UserServiceError(f"Logout failed: {e}")

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
            api_key = st.secrets["firebase"]["firebase_api"]
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }

            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Password verification failed for {email}: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Network error during password verification: {e}")
            raise AuthenticationError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during password verification: {e}")
            raise AuthenticationError(f"Verification failed: {e}")

    def save_login_logout(self, username: str, event_type: str) -> None:
        """
        Save user login/logout activity to Firestore.

        Args:
            username: User identifier
            event_type: Either 'login' or 'logout'

        Raises:
            UserServiceError: If activity logging fails
        """
        try:
            now = datetime.now()
            date = now.strftime("%d-%m-%Y")
            time = now.strftime("%H:%M:%S")

            doc_ref = self.fs.collection(
                "employee attendance").document(username)

            if event_type == "login":
                update_data = {f"activity.{date}.Login_Time": self.firebase_api.ArrayUnion([
                                                                                           time])}
            elif event_type == "logout":
                update_data = {f"activity.{date}.Logout_Time": self.firebase_api.ArrayUnion([
                                                                                            time])}
            else:
                raise ValueError(f"Invalid event_type: {event_type}")

            try:
                doc_ref.update(update_data)
            except Exception:
                # Document doesn't exist, create it
                activity_data = {
                    "activity": {
                        date: {
                            "Login_Time": [time] if event_type == "login" else [],
                            "Logout_Time": [time] if event_type == "logout" else []
                        }
                    }
                }
                doc_ref.set(activity_data, merge=True)

            logger.info(
                f"Activity logged: {username} - {event_type} at {time}")

        except Exception as e:
            logger.error(f"Failed to log activity for {username}: {e}")
            raise UserServiceError(f"Activity logging failed: {e}")

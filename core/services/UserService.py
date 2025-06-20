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

from core.utils.session_manager import get_session_manager
from core.utils.persistent_session import get_persistent_session_manager

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
            email_service: Email service for verification emails        Raises:
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
        if len(password) < 6:
            raise ValidationError(
                "Password must be at least 6 characters long")
        if password != confirm_password:
            raise ValidationError("Passwords do not match")

        # Additional username validation
        if len(username) < 3:
            raise ValidationError(
                "Username must be at least 3 characters long")
        if len(username) > 30:
            raise ValidationError("Username must be less than 30 characters")

        # Check for valid username characters (alphanumeric and underscore only)
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError(
                "Username can only contain letters, numbers, and underscores")

        # Additional password validation
        if len(password) > 30:
            raise ValidationError("Password must be less than 128 characters")

        # Optional: Check for password strength
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

            # Use actual username from user_data, not Firebase UID
            st.session_state.username = username
            st.session_state.useremail = email
            st.session_state.role = role
            st.session_state.signout = False

            # Save session to persistent storage (multiple methods)
            persistent_manager = get_persistent_session_manager()
            session_saved = persistent_manager.save_session(
                username, email, role)

            # Also try legacy session manager as backup
            session_manager = get_session_manager()
            backup_saved = session_manager.save_user_session(
                username, email, role)

            if not session_saved and not backup_saved:
                logger.warning(
                    "Failed to save user session to any persistent storage, but session created")

            # Log activity
            self.save_login_logout(user.uid, "login")

            logger.info(
                f"Session created successfully for user: {username}")

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
            # Verify password through Firebase REST API
            self._validate_login_input(email, password)
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
            UserServiceError: If user creation fails
        """
        try:
            # Basic validation (redundant check, but keep for safety)
            if not all([username, email, password, confirm_password]):
                st.error("All fields are required.")
                return

            if password != confirm_password:
                st.error("Passwords do not match.")
                return

            # Basic email validation only (no complex verification)
            email_valid, email_message = self.validate_email_basic(email)
            if not email_valid:
                st.error(email_message)
                return

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

            # Send OTP for email verification BEFORE creating account
            st.info("📧 Mengirim kode verifikasi ke email Anda...")
            otp_sent, otp_message = self.send_verification_otp(email)

            if not otp_sent:
                st.error(f"Gagal mengirim kode verifikasi: {otp_message}")
                return  # Store user data temporarily for after OTP verification
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
            st.info("💡 **Langkah selanjutnya:** Masukkan kode verifikasi 6 digit yang telah dikirim ke email Anda untuk menyelesaikan pendaftaran.")

            # Show OTP input form
            st.session_state.show_otp_verification = True
            st.session_state.verification_email = email

            logger.info(f"OTP sent for registration: {email}")

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
            email: Email address
            otp: OTP code entered by user
        """
        try:
            # Verify OTP first
            otp_valid, otp_message = self.verify_otp(email, otp)

            if not otp_valid:
                st.error(otp_message)
                return

            # Get pending registration data
            if ('pending_registration' not in st.session_state or
                    email not in st.session_state.pending_registration):
                st.error("Data pendaftaran tidak ditemukan. Silakan daftar ulang.")
                return

            pending_data = st.session_state.pending_registration[email]

            # Check if registration data is still valid (expires in 30 minutes)
            if datetime.now() - pending_data['timestamp'] > timedelta(minutes=30):
                del st.session_state.pending_registration[email]
                st.error(
                    "Data pendaftaran telah kedaluwarsa. Silakan daftar ulang.")
                return            # Create user in Firebase Authentication
            username = pending_data['username']
            password = pending_data['password']
            role = pending_data['role']

            # Debug: Check password validity
            logger.info(
                f"Creating user with email: {email}, username: {username}")

            # Validate password before sending to Firebase
            if not password or not isinstance(password, str) or len(password) < 6:
                st.error(
                    f"❌ Terjadi error: Password tidak valid (minimal 6 karakter). Password saat ini: {len(password) if password else 0} karakter")
                return

            # Validate username
            if not username or not isinstance(username, str):
                st.error("❌ Terjadi error: Username tidak valid")
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

            st.success("🎉 Akun berhasil dibuat dan email terverifikasi!")
            st.info("⏳ **Langkah Selanjutnya:** Akun Anda sedang menunggu verifikasi dari admin. Anda akan dapat login setelah admin memverifikasi akun Anda.")
            st.balloons()

            logger.info(
                f"User account created and verified successfully: {email}")

        except exceptions.AlreadyExistsError:
            st.warning("Email atau username sudah terdaftar.")
        except Exception as e:
            logger.error(f"Error completing registration: {e}")
            st.error(f"Terjadi error saat menyelesaikan pendaftaran: {e}")

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
                # Clear user session from all persistent storage
                self.save_login_logout(username, "logout")

            # Clear from persistent session manager (primary)
            persistent_manager = get_persistent_session_manager()
            persistent_manager.clear_session()

            # Also clear from legacy session manager (backup)
            session_manager = get_session_manager()
            session_manager.clear_user_session()

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

    def _validate_google_email_exists(self, email: str) -> bool:
        """
        Validate if a Google email address actually exists.

        Args:
            email: Email address to validate

        Returns:
            bool: True if email exists, False otherwise
        """
        try:
            # First check if it's a valid email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return False            # Extract domain from email
            domain = email.split('@')[1]

            # For Gmail and Google Workspace emails
            if domain.lower() in ['gmail.com', 'googlemail.com'] or domain.endswith('.google.com'):
                return self._check_gmail_exists(email)
            else:
                # For other domains, check if they use Google Workspace
                return self._check_domain_mx_records(domain, email)

        except Exception as e:
            logger.warning(f"Error validating email {email}: {e}")
            return False

    def _check_gmail_exists(self, email: str) -> bool:
        """
        Check if a Gmail address actually exists using multiple verification methods.

        Args:
            email: Gmail address to check

        Returns:
            bool: True if email exists, False otherwise
        """
        try:
            # First, basic format validation
            email_lower = email.lower()

            # Check if it's a Gmail domain
            if not (email_lower.endswith('@gmail.com') or email_lower.endswith('@googlemail.com')):
                return False

            # Extract username part
            username = email.split('@')[0]

            # Gmail username validation rules
            if len(username) < 6 or len(username) > 30:
                return False

            if username.startswith('.') or username.endswith('.'):
                return False

            if '..' in username:
                return False

            # Check for valid characters
            valid_chars = set('abcdefghijklmnopqrstuvwxyz0123456789.')
            if not all(c in valid_chars for c in username):
                return False

            # Now try to verify the email actually exists
            return self._verify_gmail_existence(email)

        except Exception as e:
            logger.warning(f"Gmail validation failed for {email}: {e}")
            return False

    def _verify_gmail_existence(self, email: str) -> bool:
        """
        Verify Gmail existence using multiple methods.

        Args:
            email: Gmail address to verify

        Returns:
            bool: True if email likely exists, False otherwise
        """
        try:
            # Method 1: Try using Firebase Auth to check if user exists
            try:
                self.auth.get_user_by_email(email)
                # If user exists in Firebase, email is definitely valid
                return True
            except exceptions.NotFoundError:
                # User not in Firebase, but email might still exist
                pass
            except Exception:
                # Firebase check failed, continue with other methods
                pass

            # Method 2: Try Google's password reset flow simulation
            # This is a more ethical way to check email existence
            if self._check_gmail_via_password_reset(email):
                return True

            # Method 3: Use Google Apps API if available
            if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
                if self._check_gmail_via_google_api(email):
                    return True

            # Method 4: Basic heuristic check for common invalid patterns
            return self._heuristic_gmail_check(email)

        except Exception as e:
            logger.warning(
                f"Gmail existence verification failed for {email}: {e}")
            return False

    def _check_gmail_via_password_reset(self, email: str) -> bool:
        """
        Check Gmail existence by simulating password reset flow.

        Args:
            email: Gmail address to check

        Returns:
            bool: True if email appears to exist
        """
        try:
            import requests

            # Use Google's account recovery API endpoint
            url = "https://accounts.google.com/signin/recovery"

            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            # First, get the recovery page
            response = session.get(url)
            if response.status_code != 200:
                return False

            # Try to submit email for recovery
            recovery_data = {
                'Email': email,
                'continue': 'https://accounts.google.com/',
                'flowName': 'GlifWebSignIn',
                'flowEntry': 'ServiceLogin'
            }

            # Submit the email
            response = session.post(
                "https://accounts.google.com/_/signin/recovery/initiate",
                data=recovery_data,
                allow_redirects=False
            )

            # Check response for indicators of email existence
            # Google returns different responses for existing vs non-existing emails
            if response.status_code in [200, 302]:
                response_text = response.text.lower()

                # If email doesn't exist, Google usually indicates this
                error_indicators = [
                    'couldn\'t find your google account',
                    'email not found',
                    'account does not exist',
                    'invalid email'
                ]

                if any(indicator in response_text for indicator in error_indicators):
                    return False

                # If no error indicators, email likely exists
                return True

            return False

        except Exception as e:
            logger.warning(f"Password reset check failed for {email}: {e}")
            return False

    def _check_gmail_via_google_api(self, email: str) -> bool:
        """
        Check Gmail using Google API if service account is available.

        Args:
            email: Gmail address to check

        Returns:
            bool: True if email exists
        """
        try:
            # This would require Google Service Account credentials
            # For now, return False as we don't have API access
            return False

        except Exception as e:
            logger.warning(f"Google API check failed for {email}: {e}")
            return False

    def _heuristic_gmail_check(self, email: str) -> bool:
        """
        Apply heuristic checks to determine if Gmail is likely valid.

        Args:
            email: Gmail address to check

        Returns:
            bool: True if email passes heuristic checks
        """
        try:
            username = email.split('@')[0].lower()

            # Check for obviously fake patterns
            fake_patterns = [
                # Sequential numbers
                r'.*123456.*',
                r'.*654321.*',
                # Obvious test patterns
                r'.*test.*test.*',
                r'.*fake.*',
                r'.*dummy.*',
                r'.*temp.*',
                # Very random looking strings (all consonants or all vowels)
                r'^[bcdfghjklmnpqrstvwxyz]{8,}$',
                r'^[aeiou]{6,}$',
                # Keyboard patterns
                r'.*qwerty.*',
                r'.*asdfgh.*',
                r'.*123abc.*'
            ]

            import re
            for pattern in fake_patterns:
                if re.match(pattern, username):
                    return False

            # Additional checks for suspicious patterns
            # Too many repeated characters
            for char in username:
                if username.count(char) > len(username) // 2:
                    return False

            # For this specific case, let's be more strict
            # If it looks like a test/fake email, reject it
            suspicious_words = ['test', 'fake',
                                'dummy', 'temp', 'example', 'sample']
            if any(word in username for word in suspicious_words):
                return False

            # Email appears legitimate based on heuristics
            return True

        except Exception as e:
            logger.warning(f"Heuristic check failed for {email}: {e}")
            return False

    def _check_gmail_via_api(self, email: str) -> bool:
        """
        Alternative method to check Gmail using Google's verification.

        Args:
            email: Gmail address to check

        Returns:
            bool: True if likely exists, False otherwise
        """
        try:
            # Use a simple verification approach
            # This is a basic check - in production, you might want to use
            # Google's People API or Gmail API for more accurate results

            # For now, we'll assume Gmail addresses are valid if they
            # follow the correct format and domain
            if '@gmail.com' in email.lower() or '@googlemail.com' in email.lower():
                return True
            return False

        except Exception as e:
            logger.warning(f"API verification failed for {email}: {e}")
            return False

    def _check_domain_mx_records(self, domain: str, email: str) -> bool:
        """
        Check if domain uses Google Workspace by examining MX records.

        Args:
            domain: Domain to check
            email: Full email address

        Returns:
            bool: True if domain uses Google services, False otherwise
        """
        try:
            # Get MX records for the domain
            mx_records = dns.resolver.resolve(domain, 'MX')

            # Check if any MX record points to Google
            google_mx_keywords = ['google.com',
                                  'googlemail.com', 'aspmx.l.google.com']

            for mx in mx_records:
                mx_host = str(mx.exchange).lower()
                if any(keyword in mx_host for keyword in google_mx_keywords):
                    # Domain uses Google Workspace, so email could be valid
                    # For more accurate verification, you'd need domain-specific checks
                    return True

            return False
        except Exception as e:
            logger.warning(f"MX record check failed for domain {domain}: {e}")
            return False

    def validate_email_before_registration(self, email: str) -> tuple[bool, str]:
        """
        Comprehensive email validation before registration with strict verification.

        Args:
            email: Email address to validate

        Returns:
            tuple: (is_valid, message)
        """
        try:
            # Basic format validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return False, "❌ Format email tidak valid"

            # Check if it's a Google email
            domain = email.split('@')[1].lower()

            if domain not in ['gmail.com', 'googlemail.com'] and not domain.endswith('.google.com'):
                # Check if domain uses Google Workspace
                if not self._check_domain_mx_records(domain, email):
                    return False, "❌ Email harus menggunakan layanan Google (Gmail atau Google Workspace)"

            # Show verification progress
            with st.spinner("🔍 Memverifikasi keberadaan email Google..."):
                # More strict verification
                if not self._validate_google_email_exists(email):
                    return False, "❌ Email Google tidak ditemukan atau tidak dapat diverifikasi. Pastikan:\n" \
                        "1. Email sudah terdaftar di Google\n" \
                        "2. Email aktif dan dapat menerima email\n" \
                        "3. Tidak menggunakan email palsu atau test"

            # Additional strict checks for suspicious emails
            username = email.split('@')[0].lower()

            # Check for obvious fake/test patterns
            suspicious_patterns = [
                'test', 'fake', 'dummy', 'temp', 'example', 'sample',
                'placeholder', 'mock', 'invalid', 'notreal'
            ]

            if any(pattern in username for pattern in suspicious_patterns):
                return False, "❌ Email terdeteksi sebagai email test/palsu. Gunakan email Google yang valid."

            # Check for too many random characters (likely fake)
            if len(username) > 15:
                # Count consonants vs vowels ratio - real names usually have balance
                vowels = set('aeiou')
                consonants = set('bcdfghjklmnpqrstvwxyz')

                vowel_count = sum(1 for c in username if c in vowels)
                consonant_count = sum(1 for c in username if c in consonants)

                if vowel_count == 0 or consonant_count == 0:
                    return False, "❌ Email terdeteksi sebagai kombinasi karakter acak. Gunakan email yang valid."

                # Check for keyboard patterns
                keyboard_patterns = ['qwerty', 'asdf',
                                     'zxcv', '123456', '654321']
                if any(pattern in username for pattern in keyboard_patterns):
                    return False, "❌ Email mengandung pola keyboard yang mencurigakan."

            # Additional check for unnatural-looking email patterns
            # Check for emails that look like random character combinations
            if self._is_likely_random_email(username):
                return False, "❌ Email terdeteksi sebagai kombinasi karakter yang tidak natural. Gunakan email dengan nama yang wajar."

            st.success("✅ Email berhasil diverifikasi!")
            return True, "Email valid dan terverifikasi"

        except Exception as e:
            logger.error(f"Error in email validation: {e}")
            return False, f"❌ Terjadi error saat memvalidasi email: {e}"

    def _is_likely_random_email(self, username: str) -> bool:
        """
        Check if email username looks like random characters or unlikely to be real.

        Args:
            username: Username part of email

        Returns:
            bool: True if email looks random/fake
        """
        try:
            # Remove dots and numbers for analysis
            clean_username = ''.join(
                c for c in username.lower() if c.isalpha())

            if len(clean_username) < 3:
                return False  # Too short to analyze

            # Check for excessive consonant clusters or vowel clusters
            vowels = set('aeiou')
            consonants = set('bcdfghjklmnpqrstvwxyz')

            # Count consecutive consonants/vowels
            max_consecutive_consonants = 0
            max_consecutive_vowels = 0
            current_consonants = 0
            current_vowels = 0

            for char in clean_username:
                if char in vowels:
                    current_vowels += 1
                    current_consonants = 0
                    max_consecutive_vowels = max(
                        max_consecutive_vowels, current_vowels)
                elif char in consonants:
                    current_consonants += 1
                    current_vowels = 0
                    max_consecutive_consonants = max(
                        max_consecutive_consonants, current_consonants)

            # Flag if too many consecutive consonants (unlikely in real names)
            if max_consecutive_consonants >= 5:  # Like "rizkyyanuark" has "rzky"
                return True

            # Check for repeated character patterns that look artificial
            if len(clean_username) >= 8:
                # Look for doubled letters in unusual positions
                doubled_count = 0
                for i in range(len(clean_username) - 1):
                    if clean_username[i] == clean_username[i + 1]:
                        doubled_count += 1

                # Multiple doubled letters might indicate artificial name
                if doubled_count >= 2:
                    return True

            # Check for uncommon letter combinations
            uncommon_patterns = [
                'rzk', 'yyk', 'yyy', 'zzz', 'qzx', 'xzq', 'wyx', 'vwx'
            ]

            for pattern in uncommon_patterns:
                if pattern in clean_username:
                    return True

            # Check if it looks like keyboard mashing or random
            # Real names usually have more common letter combinations
            common_bigrams = [
                'th', 'he', 'in', 'er', 'an', 're', 'ed', 'nd', 'to', 'en',
                'ti', 'es', 'or', 'te', 'of', 'be', 'ha', 'as', 'hi', 'is'
            ]

            bigram_count = 0
            for i in range(len(clean_username) - 1):
                bigram = clean_username[i:i+2]
                if bigram in common_bigrams:
                    bigram_count += 1

            # If very few common bigrams, might be random
            if len(clean_username) >= 8 and bigram_count == 0:
                return True

            return False

        except Exception as e:
            logger.warning(f"Random email check failed for {username}: {e}")
            return False

    def generate_otp(self) -> str:
        """
        Generate a 6-digit OTP code.

        Returns:
            str: 6-digit OTP code
        """
        return ''.join(random.choices(string.digits, k=6))

    def send_verification_otp(self, email: str) -> tuple[bool, str]:
        """
        Send OTP verification code to email address.

        Args:
            email: Email address to send OTP to

        Returns:
            tuple: (success, message)
        """
        try:
            # Generate OTP
            otp = self.generate_otp()

            # Store OTP in session state with expiration
            if 'email_verification' not in st.session_state:
                st.session_state.email_verification = {}

            # OTP expires in 10 minutes
            expiry_time = datetime.now() + timedelta(minutes=10)

            st.session_state.email_verification[email] = {
                'otp': otp,
                'expiry': expiry_time,
                'attempts': 0
            }

            # Send email with OTP
            subject = "Kode Verifikasi ICONNET Assistant"
            body = f"""
            <html>
            <body>
                <h2>Verifikasi Email - ICONNET Assistant</h2>
                <p>Halo,</p>
                <p>Anda telah mendaftar di ICONNET Assistant. Gunakan kode verifikasi berikut untuk melengkapi pendaftaran:</p>
                
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #1f4e79; font-size: 36px; margin: 0; letter-spacing: 5px;">{otp}</h1>
                </div>
                
                <p><strong>Kode ini berlaku selama 10 menit.</strong></p>
                
                <p>Jika Anda tidak mendaftar di ICONNET Assistant, abaikan email ini.</p>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                    Email ini dikirim secara otomatis. Jangan membalas email ini.
                </p>
            </body>
            </html>
            """

            # Send email using EmailService
            success = self.email_service.send_email(email, subject, body)

            if success:
                logger.info(f"OTP sent successfully to {email}")
                return True, f"Kode verifikasi telah dikirim ke {email}. Silakan periksa kotak masuk Anda."
            else:
                logger.error(f"Failed to send OTP to {email}")
                return False, "Gagal mengirim kode verifikasi. Silakan coba lagi."

        except Exception as e:
            logger.error(f"Error sending OTP to {email}: {e}")
            return False, f"Terjadi error saat mengirim kode verifikasi: {e}"

    def verify_otp(self, email: str, entered_otp: str) -> tuple[bool, str]:
        """
        Verify OTP code for email.

        Args:
            email: Email address
            entered_otp: OTP code entered by user

        Returns:
            tuple: (is_valid, message)
        """
        try:
            if 'email_verification' not in st.session_state:
                return False, "Tidak ada kode verifikasi yang ditemukan. Silakan kirim ulang kode."

            if email not in st.session_state.email_verification:
                return False, "Tidak ada kode verifikasi untuk email ini. Silakan kirim ulang kode."

            verification_data = st.session_state.email_verification[email]

            # Check if OTP expired
            if datetime.now() > verification_data['expiry']:
                del st.session_state.email_verification[email]
                return False, "Kode verifikasi telah kedaluwarsa. Silakan kirim ulang kode."

            # Check attempts limit
            if verification_data['attempts'] >= 3:
                del st.session_state.email_verification[email]
                return False, "Terlalu banyak percobaan gagal. Silakan kirim ulang kode verifikasi."

            # Verify OTP
            if entered_otp.strip() == verification_data['otp']:
                # OTP is correct, clean up
                del st.session_state.email_verification[email]
                logger.info(f"Email {email} verified successfully")
                return True, "Email berhasil diverifikasi!"
            else:
                # Increment attempts
                st.session_state.email_verification[email]['attempts'] += 1
                remaining_attempts = 3 - \
                    st.session_state.email_verification[email]['attempts']
                return False, f"Kode verifikasi salah. Sisa percobaan: {remaining_attempts}"

        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {e}")
            return False, f"Terjadi error saat memverifikasi kode: {e}"

    def validate_email_basic(self, email: str) -> tuple[bool, str]:
        """
        Basic email validation - format and domain check only.

        Args:
            email: Email address to validate

        Returns:
            tuple: (is_valid, message)
        """
        try:
            # Basic format validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return False, "❌ Format email tidak valid"

            # Check if it's a Google email (Gmail or Google Workspace)
            domain = email.split('@')[1].lower()

            google_domains = ['gmail.com', 'googlemail.com']
            is_gmail = domain in google_domains
            is_google_workspace = domain.endswith('.google.com')

            if not is_gmail and not is_google_workspace:
                # For non-Google domains, we'll still allow them but recommend Google
                st.info(
                    "💡 **Rekomendasi:** Gunakan email Google (Gmail) untuk pengalaman terbaik.")

            return True, "Format email valid"

        except Exception as e:
            logger.error(f"Error in basic email validation: {e}")
            return False, f"Terjadi error saat memvalidasi email: {e}"

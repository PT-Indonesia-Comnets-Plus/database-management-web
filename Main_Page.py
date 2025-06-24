"""
Main page for ICONNET application with user authentication and registration.
Refactored for efficiency and clean code practices.
"""

import streamlit as st
import os
from PIL import Image, ImageOps
from io import BytesIO
import base64
from typing import Tuple, Optional
import logging

from core.services.UserService import UserService
from core.services.EmailService import EmailService
from core import initialize_session_state
from core.utils.load_css import load_custom_css
from core.utils.cookies import get_cookie_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MainPageManager:
    """
    Centralized manager for the main page functionality.
    Handles authentication, UI components, and navigation.
    """

    def __init__(self):
        """Initialize the main page manager."""
        self.user_service: Optional[UserService] = None
        self.email_service: Optional[EmailService] = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize required services."""
        try:
            # initialize_session_state() akan memanggil ServiceManager
            # yang menangani pemuatan cookies dan inisialisasi semua layanan inti.
            if not initialize_session_state():
                st.error(
                    "Failed to initialize application services. Please refresh.")
                st.stop()

            # Ambil layanan dari session_state setelah inisialisasi berhasil
            self.user_service = st.session_state.get('user_service')
            self.email_service = st.session_state.get('email_service')

            # Pastikan layanan penting tersedia
            if not self.user_service or not self.email_service:
                logger.error(
                    "UserService or EmailService not found in session_state after initialization.")
                st.error(
                    "Required services are not available. Application cannot proceed.")
                st.stop()
            logger.info("MainPageManager services initialized successfully.")

        except Exception as e:
            logger.error(
                f"Critical error during MainPageManager service initialization: {e}")
            st.error(
                f"An critical error occurred while setting up services: {e}. Please try refreshing.")
            st.stop()

    def configure_page(self) -> None:
        """Configure Streamlit page settings and branding."""
        try:
            st.logo("static/image/logo_iconplus.png", size="large")
            logo = Image.open("static/image/icon.png").resize((40, 50))
            logo_with_padding = ImageOps.expand(
                logo, border=8, fill=(255, 255, 255, 0))
            st.set_page_config(
                page_title="ICONNET Assistant",
                page_icon=logo_with_padding,
                layout="centered",
                initial_sidebar_state="collapsed"
            )
        except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
            # Ini normal jika set_page_config bukan perintah pertama di halaman lain
            pass
        except FileNotFoundError:
            logger.warning("Page icon file (static/image/icon.png) not found.")
        except Exception as e:
            logger.warning(f"Could not load page icon: {e}")

    def load_styles(self) -> None:
        """Load custom CSS styles."""
        css_path = os.path.join("static", "css", "style.css")
        if os.path.exists(css_path):
            load_custom_css(css_path)
        else:
            logger.warning(f"Custom CSS file not found at {css_path}")

    @staticmethod
    def image_to_base64(image: Image.Image) -> str:
        """
        Mengonversi gambar ke format base64 untuk ditampilkan di Streamlit.
        """
        try:
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            # Return the full data URI scheme
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""  # Kembalikan string kosong jika error

    def display_header(self) -> None:
        """Display application header with logo and title."""
        try:
            # Centered Logo
            logo_home_path = "static/image/logo_Iconnet.png"
            if os.path.exists(logo_home_path):
                logo_home = Image.open(logo_home_path)
                logo_base64 = MainPageManager.image_to_base64(logo_home)
                if logo_base64:  # Pastikan konversi berhasil
                    st.markdown(
                        f"""
                        <div style="text-align: center; padding-bottom: 10px;">
                            <img src="{logo_base64}" alt="ICONNET Logo" style="width: 100%; max-width: 400px;">
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                logger.warning(f"Main logo file not found: {logo_home_path}")

            # Centered Subtitle
            st.markdown(
                """
                <p style='text-align: center; color: #666; font-size: 16px; margin-top: 0px;'>
                    Database Management & AI Assistant Platform
                </p>                """,
                unsafe_allow_html=True
            )

        except Exception as e:
            logger.error(f"Error displaying header: {e}")
            # Fallback display in case of any error
            st.markdown(
                "<p style='text-align: center; color: #666; font-size: 16px;'>Database Management & AI Assistant Platform</p>",
                unsafe_allow_html=True
            )

    def is_user_authenticated(self) -> bool:
        """Check if user is currently authenticated and session is valid."""
        try:
            # First check basic session state
            username_exists = bool(
                st.session_state.get("username", "").strip())
            is_signed_out = st.session_state.get("signout", True)

            logger.info(
                f"🔍 Authentication check - username: {username_exists}, signout: {is_signed_out}")

            # If no username or signed out, not authenticated
            if not username_exists or is_signed_out:
                logger.info("❌ Not authenticated - no username or signed out")
                return False

            # If user service is available, do additional validation
            if self.user_service:
                # Use UserService to check session validity (includes timeout check)
                session_valid = self.user_service.is_session_valid()
                logger.info(
                    f"🔍 UserService session validation: {session_valid}")

                if not session_valid:
                    # Session is invalid/expired, perform logout
                    logger.info(
                        f"❌ Session validation failed for user: {username_exists}")
                    self.user_service.logout_if_expired()
                    return False

            # User is authenticated if username exists and not signed out
            logger.info(
                f"✅ User authenticated: {st.session_state.get('username', '')}")
            return True

        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            # Fallback to simple check
            username_exists = bool(
                st.session_state.get("username", "").strip())
            is_signed_out = st.session_state.get("signout", True)
            return username_exists and not is_signed_out

    def check_and_restore_session(self) -> bool:
        """
        Check and restore user session automatically.
        This should be called on every page load.

        Returns:
            bool: True if user is authenticated, False otherwise
        """
        try:
            # Use global persistent session check first
            from core.utils.cookies import check_and_restore_persistent_session
            session_restored = check_and_restore_persistent_session()

            if session_restored:
                return True

            # Check if user service is available for additional restoration
            if not self.user_service:
                logger.warning("UserService not available for session check")
                return False

            # Try to restore session using UserService
            if self.user_service.restore_user_session():
                # Validate the restored session
                if self.user_service.is_session_valid():
                    username = st.session_state.get("username", "")
                    logger.info(f"🟢 Valid session confirmed for: {username}")
                    return True
                else:
                    logger.debug("Restored session is invalid or expired")
                    return False
            else:
                logger.debug("No session to restore via UserService")
                return False

        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False

    def show_persistent_session_info(self) -> None:
        """Show information about session persistence to user."""
        if st.session_state.get("username"):
            username = st.session_state.get("username", "")
            # Show a subtle indicator that user is logged in
            with st.sidebar:
                st.success(f"🔒 Logged in as: {username}")
                if st.button("🚪 Logout", key="persistent_logout"):
                    self.handle_logout()

    def display_authentication_form(self) -> None:
        """Display authentication forms (login/register)."""
        st.markdown("---")

        # Authentication method selection
        auth_method = st.radio(
            "Choose method:",
            ["Login", "Register"],
            horizontal=True,
            key="auth_method_main_page"  # Key unik untuk radio button ini
        )

        if auth_method == "Login":
            self._display_login_form()
        else:
            self._display_registration_form()

    def _display_login_form(self) -> None:
        """Display login form."""
        st.subheader("🔐 Login")

        with st.form("login_form_main", clear_on_submit=False):  # Key unik untuk form
            email = st.text_input(
                "Email", placeholder="user@iconnet.com", key="main_login_email")
            password = st.text_input(
                "Password", type="password", key="main_login_password")
            login_button = st.form_submit_button(
                "Login", use_container_width=True)

            if login_button:
                if self.user_service:
                    self._handle_login(email, password)
                else:
                    st.error("User service not available. Cannot process login.")

    def _display_registration_form(self) -> None:
        """Display registration form."""
        st.subheader("📝 Register")        # Check if OTP verification is needed
        if st.session_state.get('show_otp_verification', False):
            self._display_otp_verification_form()
            return

        # Information about requirements
        st.info("📧 **Persyaratan Pendaftaran:**\n"
                "• Email Google (Gmail atau Google Workspace) yang aktif\n"
                "• Username 3-30 karakter (huruf, angka, underscore)\n"
                "• Password minimal 6 karakter dengan huruf besar, kecil, dan angka")

        with st.form("register_form_main", clear_on_submit=False):
            st.markdown("#### 📝 **Informasi Akun**")

            col1, col2 = st.columns(2)

            with col1:
                username = st.text_input(
                    "Username",
                    placeholder="johndoe",
                    help="Username unik 3-30 karakter (huruf, angka, underscore)",
                    key="main_reg_username")
                email = st.text_input(
                    "Email",
                    placeholder="john@gmail.com",
                    help="Email Google yang aktif untuk menerima kode verifikasi",
                    key="main_reg_email")

            with col2:
                password = st.text_input(
                    "Password",
                    type="password",
                    help="Minimal 6 karakter dengan huruf besar, kecil, dan angka",
                    key="main_reg_password")
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    help="Ulangi password yang sama persis",
                    key="main_reg_confirm_password")

            st.markdown("---")
            register_button = st.form_submit_button(
                "🚀 Daftar Sekarang", use_container_width=True, type="primary")

            if register_button:
                if self.user_service:
                    self._handle_registration(
                        username, email, password, confirm_password)
                else:
                    st.error(
                        "User service not available. Cannot process registration.")

    def _handle_login(self, email: str, password: str) -> None:
        """Handle login form submission with enhanced cookie persistence."""
        if not email or not password:
            st.warning("Please fill in all fields.")
            return

        # Simulasi validasi sederhana untuk demo (ganti dengan validasi sebenarnya)
        demo_login = False
        if email == "user@iconnet.com" and password == "pass123":
            demo_login = True

        with st.spinner("Authenticating..."):
            try:
                if demo_login:
                    # Demo login berhasil
                    import time
                    from core.utils.cookies import get_cloud_cookie_manager
                    cookie_manager = get_cloud_cookie_manager()

                    # Simpan sesi ke cookies dan session state
                    success = cookie_manager.save_user_session(
                        username="demo_user",
                        email=email,
                        role="user"
                    )

                    if success:
                        st.success("🎉 Login berhasil! Selamat datang!")
                        logger.info(
                            "🎉 Demo login successful, user authenticated!")
                        # Clear any error states
                        if 'login_error' in st.session_state:
                            del st.session_state['login_error']
                        time.sleep(1)  # Brief delay to show success message
                        st.rerun()
                    else:
                        st.error("Login berhasil tetapi gagal menyimpan sesi.")

                elif self.user_service:
                    # UserService.login akan menangani st.success/st.warning/st.error
                    # dan pembaruan st.session_state serta cookies.
                    # Jika login berhasil, UserService akan mengatur session state
                    # Force check authentication status after login attempt
                    self.user_service.login(email, password)
                    if self.is_user_authenticated():
                        logger.info("🎉 Login successful, user authenticated!")
                        # Clear any error states
                        if 'login_error' in st.session_state:
                            del st.session_state['login_error']
                        st.rerun()
                else:
                    st.error(
                        "❌ Email atau password salah. Untuk demo, gunakan:\n- Email: user@iconnet.com\n- Password: pass123")

            except Exception as e:  # Menangkap error tak terduga dari UserService.login
                logger.error(f"Unexpected error during login handling: {e}")
                st.error("An unexpected error occurred during login.")

    def _handle_registration(self, username: str, email: str, password: str, confirm_password: str) -> None:
        """Handle registration form submission."""
        # Basic field validation
        if not all([username, email, password, confirm_password]):
            st.warning("Please fill in all fields.")
            return

        # Password confirmation validation
        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        # Advanced validation before sending OTP
        try:
            # Username validation
            if len(username) < 3:
                st.error("Username must be at least 3 characters long.")
                return
            if len(username) > 30:
                st.error("Username must be less than 30 characters.")
                return

            # Check for valid username characters (alphanumeric and underscore only)
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                st.error(
                    "Username can only contain letters, numbers, and underscores.")
                return

            # Password strength validation
            if len(password) < 6:
                st.error("Password must be at least 6 characters long.")
                return
            if len(password) > 128:
                st.error("Password must be less than 128 characters.")
                return

            # Check for password strength requirements
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)

            if not (has_upper and has_lower and has_digit):
                st.error(
                    "Password must contain at least one uppercase letter, one lowercase letter, and one number.")
                return

            # Basic email format validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                st.error("Please enter a valid email address.")
                return

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            st.error("An error occurred during validation. Please try again.")
            return

        # All validations passed, now proceed with registration
        with st.spinner("Creating account..."):
            try:
                # UserService.signup akan menangani st.success/st.warning/st.error
                # dan mengatur show_otp_verification = True jika OTP berhasil dikirim
                self.user_service.signup(
                    username, email, password, confirm_password, role="Employee")

                # Jika OTP verification diminta, rerun untuk menampilkan form OTP
                if st.session_state.get('show_otp_verification', False):
                    st.rerun()

            except Exception as e:  # Menangkap error tak terduga dari UserService.signup
                logger.error(
                    f"Unexpected error during registration handling: {e}")
                st.error("An unexpected error occurred during registration.")

    def display_user_dashboard(self) -> None:
        """Display user dashboard for authenticated users."""
        st.markdown("---")

        # Welcome section
        self._display_welcome_section()

        # Navigation section
        self._display_navigation_section()

    def _display_welcome_section(self) -> None:
        """Display welcome message and user info."""
        col1, col2, col3 = st.columns(
            [2, 1, 1])  # Sesuaikan rasio kolom jika perlu

        with col1:
            username = st.session_state.get('username', 'User')
            role = st.session_state.get('role', 'User')
            email_display = st.session_state.get('useremail', 'N/A')

            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                    <h3 style='color: #1f4e79; margin: 0;'>
                        Welcome, {username}! 👋
                    </h3>
                    <p style='margin: 5px 0 0 0; color: #666;'>
                        Email: {email_display} | Role: {role}
                    </p>
                </div>
            """, unsafe_allow_html=True)

        with col2:  # Session info
            if self.user_service:
                session_info = self.user_service.get_session_info()
                if session_info.get('is_valid'):
                    remaining_hours = session_info.get('remaining_hours', 0)
                    if remaining_hours < 1:
                        remaining_minutes = session_info.get(
                            'remaining_minutes', 0)
                        time_display = f"{remaining_minutes:.0f} menit"
                        if remaining_minutes < 30:
                            st.warning(
                                f"⏱️ Sesi berakhir dalam {time_display}")
                        else:
                            st.info(f"⏱️ Sesi: {time_display}")
                    else:
                        time_display = f"{remaining_hours:.1f} jam"
                        st.info(f"⏱️ Sesi: {time_display}")
                else:
                    st.error("❌ Sesi tidak valid")

        with col3:  # Tombol logout di kolom paling kanan
            if st.button("🚪 Logout", use_container_width=True, key="main_page_logout_button"):
                self._handle_logout()

    def _display_navigation_section(self) -> None:
        """Display navigation buttons for different features."""
        st.markdown("### 📋 Available Features")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🏠 Home Dashboard", use_container_width=True, key="nav_home_dashboard"):
                st.switch_page("pages/1 Home Page.py")

        with col2:
            user_role = st.session_state.get('role', '')
            if user_role.lower() == 'admin':  # Perbandingan case-insensitive
                if st.button("⚙️ Admin Panel", use_container_width=True, key="nav_admin_panel"):
                    st.switch_page("pages/2 Admin Page.py")
            # else:
                # Tidak perlu menampilkan info jika bukan admin, biarkan kosong atau isi dengan fitur lain
                # st.info("Admin access required for Admin Panel")

    def _handle_logout(self) -> None:
        """Handle user logout."""
        try:
            if self.user_service:
                self.user_service.logout()  # Ini akan membersihkan session state dan cookies
                st.rerun()  # Rerun untuk memperbarui UI ke kondisi logout
            else:
                logger.error(
                    "UserService not available during logout attempt.")
                self._fallback_logout()  # Coba fallback jika service tidak ada
        except Exception as e:
            logger.error(f"Error during UserService logout: {e}")
            self._fallback_logout()  # Coba fallback jika ada error di service logout

    def _fallback_logout(self) -> None:
        """Fallback logout method if UserService fails or is unavailable."""
        logger.warning("Executing fallback logout.")
        try:
            # Clear cookies
            # Ini juga akan mencoba membersihkan session state
            get_cookie_manager().clear_user()

            # Eksplisit membersihkan session state yang relevan dengan sesi pengguna
            # Hati-hati jangan menghapus state yang dibutuhkan oleh layanan inti jika mereka
            # di-cache atau dimaksudkan untuk persisten antar sesi (meskipun jarang untuk data pengguna).
            user_session_keys = ["username", "useremail",
                                 "role", "signout", "messages", "thread_id"]
            for key in user_session_keys:
                if key in st.session_state:
                    del st.session_state[key]

            # Pastikan signout diatur ke True
            st.session_state.signout = True

            st.success("Logged out successfully (fallback).")
            st.rerun()

        except Exception as e:
            logger.error(f"Error during fallback logout: {e}")
            st.error("Error during logout. Please refresh the page.")

    def _display_otp_verification_form(self) -> None:
        """Display OTP verification form."""
        st.subheader("🔐 Verifikasi Email")

        verification_email = st.session_state.get('verification_email', '')

        # Informasi lengkap tentang proses verifikasi
        st.success(
            f"📧 **Kode verifikasi telah dikirim ke:** {verification_email}")

        col1, col2 = st.columns([2, 1])

        with col1:
            otp_input = st.text_input(
                "Kode Verifikasi (6 digit)",
                placeholder="123456",
                max_chars=6,
                help="Masukkan kode 6 digit yang dikirim ke email Anda",
                key="otp_verification_input"
            )

        with col2:
            st.write("")  # Space
            verify_button = st.button(
                "✅ Verifikasi", use_container_width=True, type="primary")

        # Action buttons
        st.markdown("---")
        col3, col4, col5 = st.columns([1, 1, 1])

        with col3:
            if st.button("📧 Kirim Ulang Kode", use_container_width=True):
                if self.user_service:
                    with st.spinner("Mengirim ulang kode..."):
                        success, message = self.user_service.send_verification_otp(
                            verification_email)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.error("User service not available.")

        with col4:
            if st.button("❓ Tidak Terima Email?", use_container_width=True):
                st.info("""
                **Jika Anda tidak menerima email:**
                - 📂 Periksa folder **Spam/Junk**
                - ⏳ Tunggu 1-2 menit
                - 📧 Pastikan email yang dimasukkan benar
                - 🔄 Coba tombol "Kirim Ulang Kode"
                """)

        with col5:
            if st.button("❌ Batal", use_container_width=True):
                # Clean up verification state
                if 'show_otp_verification' in st.session_state:
                    del st.session_state.show_otp_verification
                if 'verification_email' in st.session_state:
                    del st.session_state.verification_email
                if 'pending_registration' in st.session_state and verification_email in st.session_state.pending_registration:
                    del st.session_state.pending_registration[verification_email]
                st.rerun()        # Handle verification
        if verify_button and otp_input:
            if self.user_service:
                if len(otp_input) != 6 or not otp_input.isdigit():
                    st.error("❌ Kode verifikasi harus 6 digit angka!")
                else:
                    with st.spinner("Memverifikasi kode..."):
                        self.user_service.complete_registration_after_otp(
                            verification_email, otp_input)
            else:
                st.error("User service not available.")
        elif verify_button:
            st.warning("⚠️ Masukkan kode verifikasi terlebih dahulu.")

    def display_main_page(self) -> None:
        """Display main page after user is authenticated."""
        username = st.session_state.get("username", "Guest")

        # Header untuk halaman utama
        st.markdown(f"""
        <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;'>
            <h1 style='color: #1f77b4; margin-bottom: 10px;'>🎉 Selamat Datang, {username}!</h1>
            <p style='color: #666; font-size: 18px;'>Anda berhasil login ke sistem Database Management & AI Assistant Platform</p>
        </div>
        """, unsafe_allow_html=True)

        # Info sesi
        col1, col2, col3 = st.columns(3)

        with col1:
            st.info(f"👤 **Username:** {username}")

        with col2:
            email = st.session_state.get("useremail", "N/A")
            st.info(f"📧 **Email:** {email}")

        with col3:
            role = st.session_state.get("role", "user").title()
            st.info(f"🔐 **Role:** {role}")

        # Session info
        session_expiry = st.session_state.get("session_expiry", 0)
        if session_expiry > 0:
            import datetime
            expiry_time = datetime.datetime.fromtimestamp(session_expiry)
            st.success(
                f"⏰ **Session aktif sampai:** {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")

        st.markdown("---")

        # Demo fitur aplikasi
        st.subheader("🚀 Fitur Aplikasi")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### 📊 Database Management
            - Kelola data asset perusahaan
            - Import/export data Excel
            - Visualisasi data interaktif
            - Backup dan restore database
            """)

            if st.button("🔗 Akses Database", use_container_width=True):
                st.info("Fitur database akan tersedia di halaman khusus")

        with col2:
            st.markdown("""
            ### 🤖 AI Assistant
            - Chat dengan AI untuk analisis data
            - Rekomendasi optimasi database
            - Generate laporan otomatis
            - Natural language queries
            """)

            if st.button("💬 Chat dengan AI", use_container_width=True):
                st.info("Fitur AI Assistant akan tersedia di halaman khusus")

        st.markdown("---")

        # Logout section
        st.subheader("⚙️ Pengaturan Akun")

        col1, col2, col3 = st.columns([1, 1, 1])

        with col2:
            if st.button("🚪 Logout", type="primary", use_container_width=True):
                self.handle_logout()

    def handle_logout(self) -> None:
        """Handle user logout with proper cookie cleanup."""
        try:
            # Get cookie manager and clear session
            from core.utils.cookies import get_cloud_cookie_manager
            cookie_manager = get_cloud_cookie_manager()

            # Clear both session state and cookies
            success = cookie_manager.clear_user_session()

            if success:
                st.success(
                    "✅ Logout berhasil! Terima kasih telah menggunakan aplikasi kami.")
                logger.info(
                    f"User {st.session_state.get('username', 'unknown')} logged out successfully")

                # Clear any additional session states
                for key in list(st.session_state.keys()):
                    if key.startswith(('login_', 'user_', 'auth_')):
                        del st.session_state[key]

                # Use UserService logout if available
                if self.user_service:
                    self.user_service.logout()

                # Wait a moment then rerun
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.warning(
                    "Logout berhasil tetapi ada masalah membersihkan sesi.")
                st.rerun()

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            # Force clear session state anyway
            st.session_state.username = ""
            st.session_state.useremail = ""
            st.session_state.role = ""
            st.session_state.signout = True
            st.error(
                "Terjadi kesalahan saat logout, namun Anda telah dikeluarkan dari sistem.")
            st.rerun()

    def display_login_demo_info(self) -> None:
        """Display demo login information."""
        st.markdown("""
        <div style='background-color: #e8f4fd; padding: 15px; border-radius: 8px; margin: 10px 0;'>
            <h4 style='color: #1f77b4; margin-top: 0;'>🎯 Demo Login Information</h4>
            <p><strong>Email:</strong> user@iconnet.com</p>
            <p><strong>Password:</strong> pass123</p>
            <p style='font-size: 12px; color: #666; margin-bottom: 0;'>
                <em>Gunakan kredensial di atas untuk mencoba fitur persistent login dengan cookies</em>
            </p>
        </div>
        """, unsafe_allow_html=True)

    def run(self) -> None:
        """Main application entry point."""
        self.configure_page()
        self.load_styles()

        # Check and restore session automatically
        session_restored = self.check_and_restore_session()
        logger.info(f"🔄 Session restoration result: {session_restored}")

        self.display_header()

        # Check authentication status
        is_authenticated = self.is_user_authenticated()
        logger.info(f"🔍 Final authentication status: {is_authenticated}")

        if is_authenticated:
            logger.info("📱 Displaying user dashboard")
            # Show persistent session info in sidebar
            self.show_persistent_session_info()
            self.display_user_dashboard()
        else:
            logger.info("🔐 Displaying authentication form")
            self.display_authentication_form()


def main():
    """Application entry point."""
    try:
        app = MainPageManager()
        app.run()
    except Exception as e:  # Menangkap error yang mungkin tidak tertangkap di dalam MainPageManager.run()
        logger.critical(
            f"Unhandled application error in main(): {e}", exc_info=True)
        st.error(
            "An critical unexpected error occurred. Please refresh the page or contact support.")


if __name__ == "__main__":
    main()

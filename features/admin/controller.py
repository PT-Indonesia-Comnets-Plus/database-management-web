import streamlit as st
from core.services.UserService import UserService
from core.services.UserDataService import UserDataService
from streamlit_option_menu import option_menu
from core import initialize_session_state
from PIL import Image, ImageOps
from .views import dashboard, rag, verify_users


class AdminPage:
    def __init__(self, firestore, auth, firestore_config):
        self.user_data_service = UserDataService(
            firestore)

    def configure_page(self):
        """Konfigurasi halaman Streamlit."""
        try:
            logo = Image.open("static/image/icon.png").resize((40, 50))
            logo_with_padding = ImageOps.expand(
                logo, border=8, fill=(255, 255, 255, 0)
            )
            st.set_page_config(page_title="Admin Page",
                               page_icon=logo_with_padding)
        except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
            pass
        st.logo("static/image/logo_iconplus.png", size="large")

    def load_css(self, file_path):
        """Muat file CSS ke dalam aplikasi Streamlit."""
        try:
            with open(file_path) as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        except FileNotFoundError:
            st.error("CSS file not found.")

    def render_sidebar(self):
        """Render menu navigasi di sidebar."""
        with st.sidebar:
            app = option_menu(
                menu_title="Select Menu",
                options=["Dashboard", "Verify Users",
                         "RAG"],
                icons=["grid", "search", "table"],
                default_index=0,
                orientation="vertical",
                styles={
                    "container": {"padding": "1px", "background-color": "#E3F2FD"},
                    "menu-title": {"font-size": "24px", "font-weight": "bold", "color": "#546E7A"},
                    "icon": {"color": "#546E7A", "font-size": "18px"},
                    "nav-link": {"color": "#546E7A", "font-size": "18px", "text-align": "left", "margin": "5px"},
                    "nav-link-selected": {"background-color": "#42c2ff", "color": "#FFFFFF", "font-weight": "bold"},
                }
            )
        return app

    def render_page(self, app):
        """Render sub-halaman berdasarkan pilihan menu."""
        if app == 'Dashboard':
            dashboard.app(self.user_data_service)
        elif app == 'Verify Users':
            verify_users.app()
        elif app == 'RAG':
            rag.app()

    def render(self):
        self.configure_page()
        initialize_session_state()
        self.load_css("static/css/style.css")

        # Periksa apakah pengguna sudah login
        if "username" not in st.session_state or not st.session_state.username:
            st.warning("You must log in first to access this page.")
            return  # Hentikan rendering jika pengguna belum login

        # Periksa apakah pengguna memiliki role "Admin"
        if "role" not in st.session_state or st.session_state.role != "Admin":
            st.warning(
                "You are not authorized to view this page. Only admins can access this page."
            )
            return  # Hentikan rendering konten admin, tetapi tetap tampilkan elemen umum

        # Jika pengguna sudah login dan memiliki role "Admin", render halaman
        app = self.render_sidebar()
        self.render_page(app)

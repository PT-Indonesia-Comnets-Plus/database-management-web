import streamlit as st
from PIL import Image, ImageOps
from streamlit_option_menu import option_menu
from sub_pages.home import dashboard, search, update_data, chatbot, update
from utils.database import connect_db
from utils.firebase_config import get_firebase_app
from utils.cookies import load_cookie_to_session


class HomePage:
    def __init__(self):
        # Inisialisasi atribut yang diperlukan
        self.fs = None
        self.db_connection = None

    def initialize_session_state(self):
        """Inisialisasi atribut session_state jika belum ada."""
        if "username" not in st.session_state:
            load_cookie_to_session(st.session_state)

        if "db_connection" not in st.session_state:
            # Store the database connection in session_state
            st.session_state.db_connection = connect_db()
            st.session_state.connection_active = True

        if "fs" not in st.session_state:
            st.session_state.fs, st.session_state.auth = get_firebase_app()

        # Simpan referensi Firestore ke atribut kelas
        self.fs = st.session_state.fs
        self.db_connection = st.session_state.db_connection

    def configure_page(self):
        """Konfigurasi halaman Streamlit."""
        # Set logo di sidebar
        st.logo("static/image/logo_iconplus.png", size="large")

        # Load dan resize logo
        logo = Image.open("static/image/icon.png")
        logo_resized = logo.resize((40, 50))
        padding = 8
        logo_with_padding = ImageOps.expand(
            logo_resized, border=padding, fill=(255, 255, 255, 0)
        )

        # Set konfigurasi halaman
        try:
            st.set_page_config(page_title="Home Page",
                               page_icon=logo_with_padding)
        except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
            pass

    def load_css(self, file_path):
        """Muat file CSS ke dalam aplikasi Streamlit."""
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def render_sidebar(self):
        """Render menu navigasi di sidebar."""
        with st.sidebar:
            app = option_menu(
                menu_title="Select Menu",
                options=["Dashboard", "Search",
                         "Update Data", "Chatbot", "Test"],
                icons=["grid", "search", "table", "chat", "code"],
                default_index=0,
                orientation="vertical",
                styles={
                    "container": {"padding": "1px", "background-color": "#E3F2FD"},
                    "menu-title": {"font-size": "24px", "font-weight": "bold", "color": "#546E7A"},
                    "icon": {
                        "color": "#546E7A",
                        "font-size": "18px",
                    },
                    "nav-link": {
                        "color": "#546E7A",
                        "font-size": "18px",
                        "text-align": "left",
                        "margin": "5px",
                    },
                    "nav-link-selected": {
                        "background-color": "#42c2ff",
                        "color": "#FFFFFF",
                        "font-weight": "bold",
                    },
                    "nav-link-selected .icon": {
                        "color": "#FFFFFF",
                    },
                }
            )
        return app

    def render_page(self, app):
        """Render sub-halaman berdasarkan pilihan menu."""
        if app == 'Dashboard':
            dashboard.app()
        elif app == 'Search':
            search.app()
        elif app == 'Update Data':
            update_data.app()
        elif app == 'Chatbot':
            chatbot.app()
        elif app == 'Test':
            update.app()

    def render(self):
        """Render seluruh halaman Home Page."""
        # Inisialisasi session state
        self.initialize_session_state()

        # Konfigurasi halaman
        self.configure_page()

        # Muat file CSS
        self.load_css("static/css/style.css")

        # Render sidebar dan dapatkan pilihan menu
        app = self.render_sidebar()

        # Render sub-halaman berdasarkan pilihan menu
        self.render_page(app)

# features/home/controller.py

import streamlit as st
from PIL import Image, ImageOps
from streamlit_option_menu import option_menu
# Import views
from .views import dashboard, search, update_data, chatbot, update, chatbot2
# Import services dan init function
from core import initialize_session_state
from core.services.AssetDataService import AssetDataService  # Import service
from psycopg2 import pool  # Import pool untuk type hinting db_pool


class HomePage:
    """Controller for the Home section."""

    def __init__(self, asset_data_service: AssetDataService, db_pool: pool.SimpleConnectionPool):
        """
        Initializes the HomePage controller.

        Args:
            asset_data_service: Instance of AssetDataService.
            db_pool: Instance of the database connection pool (for views needing direct access).
        """
        self.asset_data_service = asset_data_service
        self.db_pool = db_pool
        # self.fs = None # Tidak perlu lagi jika tidak digunakan langsung di controller

    def configure_page(self):
        """Configures Streamlit page settings."""
        try:
            logo = Image.open("static/image/icon.png").resize((40, 50))
            logo_with_padding = ImageOps.expand(
                logo, border=8, fill=(255, 255, 255, 0))
        except st.errors.StreamlitAPIException:
            pass
        except FileNotFoundError:
            st.warning("Logo icon file not found.")
        st.logo("static/image/logo_iconplus.png", size="large")

    def load_css(self, file_path: str):
        """Loads a CSS file into the Streamlit app."""
        try:
            with open(file_path) as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        except FileNotFoundError:
            st.error(f"CSS file not found at: {file_path}")

    def render_sidebar(self) -> str:
        """Renders the navigation menu in the sidebar."""
        with st.sidebar:
            # Sesuaikan options dan icons jika perlu
            selected_option = option_menu(
                menu_title="Main Menu",  # Ganti judul
                options=["Dashboard", "Search Assets", "Upload Assets", "Chatbot",
                         "Edit/Delete Assets", "SQL Chatbot"],  # Nama lebih deskriptif
                icons=["speedometer2", "search", "cloud-upload", "chat-dots",
                       "pencil-square", "database"],  # Sesuaikan ikon
                menu_icon="house-door-fill",  # Ikon menu utama
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
        return selected_option

    def render_page(self, selected_option: str):
        """Renders the sub-page based on the menu selection."""
        # Panggil view dengan dependensi yang diperlukan
        if selected_option == 'Dashboard':
            dashboard.app(self.asset_data_service)  # Butuh AssetDataService
        elif selected_option == 'Search Assets':
            search.app(self.asset_data_service)  # Butuh AssetDataService
        elif selected_option == 'Upload Assets':
            update_data.app(self.asset_data_service)  # Butuh AssetDataService
        elif selected_option == 'Chatbot':
            chatbot.app()  # Chatbot.app tidak butuh dependensi langsung (menggunakan graph)
        elif selected_option == 'SQL Chatbot':
            chatbot2.app()  # Chatbot2 butuh db_pool
        elif selected_option == 'Edit/Delete Assets':
            update.app(self.asset_data_service)  # Butuh AssetDataService

    def render(self):
        """Renders the complete Home Page."""
        self.configure_page()
        self.load_css("static/css/style.css")

        # --- Authentication Check ---
        if "username" not in st.session_state or not st.session_state.username:
            st.warning("🔒 You must log in first to access this page.")
            st.page_link("Main_Page.py", label="Go to Login", icon="🏠")
            return  # Stop rendering further
        # --- End Check ---

        # Render sidebar and selected page content if authenticated
        selected_option = self.render_sidebar()
        self.render_page(selected_option)

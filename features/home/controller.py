# features/home/controller.py

import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_option_menu import option_menu
# Import views
from .views import dashboard, search, update_data, chatbot, update
# Import services dan init function
from core.services.AssetDataService import AssetDataService
from psycopg2 import pool
from core.utils.load_css import load_custom_css


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

    def configure_page(self):
        """Configures Streamlit page settings."""
        try:
            logo = Image.open("static/image/icon.png").resize((40, 50))
            logo_with_padding = ImageOps.expand(
                logo, border=8, fill=(255, 255, 255, 0))
            st.set_page_config(page_title="Home Page",
                               page_icon=logo_with_padding)
        except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
            pass
        st.logo("static/image/logo_iconplus.png", size="large")

    def render_sidebar(self) -> str:
        """Renders the navigation menu in the sidebar."""
        with st.sidebar:
            # Sesuaikan options dan icons jika perlu
            selected_option = option_menu(
                menu_title="Main Menu",
                options=["Dashboard", "Search Assets", "Upload Assets", "Chatbot",
                         "Edit/Delete Assets"],
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
            dashboard.app(self.asset_data_service)
        elif selected_option == 'Search Assets':
            search.app(self.asset_data_service)
        elif selected_option == 'Upload Assets':
            update_data.app(self.asset_data_service)
        elif selected_option == 'Chatbot':
            chatbot.app()
        elif selected_option == 'Edit/Delete Assets':
            update.app(self.asset_data_service)

    def render(self):
        """Renders the complete Home Page."""
        self.configure_page()
        # Load custom CSS
        load_custom_css(os.path.join("static", "css", "style.css"))

        # --- Authentication Check ---
        if "username" not in st.session_state or not st.session_state.username:
            st.warning("🔒 You must log in first to access this page.")
            st.page_link("Main_Page.py", label="Go to Login", icon="🏠")
            return
        selected_option = self.render_sidebar()
        self.render_page(selected_option)

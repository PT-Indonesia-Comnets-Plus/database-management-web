import streamlit as st
from PIL import Image, ImageOps
from streamlit_option_menu import option_menu
from sub_pages.home import dashboard, search, update_data, chatbot, update
from utils import initialize_session_state


class HomePage:
    def __init__(self):
        self.fs = None
        self.db_connection = None

    def configure_page(self):
        """Konfigurasi halaman Streamlit."""
        try:
            logo = Image.open("static/image/icon.png").resize((40, 50))
            logo_with_padding = ImageOps.expand(
                logo, border=8, fill=(255, 255, 255, 0)
            )
            st.set_page_config(page_title="Home Page",
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
                options=["Dashboard", "Search",
                         "Update Data", "Chatbot", "Test"],
                icons=["grid", "search", "table", "chat", "code"],
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
        self.configure_page()
        initialize_session_state()
        self.load_css("static/css/style.css")
        app = self.render_sidebar()
        self.render_page(app)

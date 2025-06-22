import streamlit as st
# Import type hinting untuk services
from core.services.UserService import UserService
from core.services.UserDataService import UserDataService
from streamlit_option_menu import option_menu
from core import initialize_session_state
from PIL import Image, ImageOps
from .views import dashboard, rag, verify_users
from core.services.RAG import RAGService
from core.utils.session_manager import ensure_valid_session, display_session_warning


class AdminPage:
    """Controller for the Admin section."""

    # Terima instance service di __init__
    def __init__(self,
                 user_service: UserService,
                 user_data_service: UserDataService,
                 rag_service: RAGService
                 ):
        """
        Initializes the AdminPage controller.

        Args:
            user_service: Instance of UserService.
            user_data_service: Instance of UserDataService.
            rag_service: Instance of RAGService.
        """
        self.user_service = user_service
        self.user_data_service = user_data_service
        self.rag_service = rag_service

    def configure_page(self):
        """Configures Streamlit page settings."""
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
            # Ensure options match the keys used in render_page
            selected_option = option_menu(
                menu_title="Admin Menu",
                options=["Dashboard", "Verify Users",
                         "RAG Management"],
                icons=["grid-fill", "person-check-fill",
                       "file-earmark-arrow-up-fill"],
                menu_icon="person-workspace",
                default_index=0,
                orientation="vertical",
                styles={
                    "container": {"padding": "1px", "background-color": "#E3F2FD"},
                    "menu-title": {"font-size": "24px", "font-weight": "bold", "color": "#546E7A"},
                    "icon": {"color": "#546E7A", "font-size": "18px"},
                    "nav-link": {"color": "#546E7A", "font-size": "18px", "text-align": "left", "margin": "5px"},
                    "nav-link-selected": {"background-color": "#42c2ff", "color": "#FFFFFF", "font-weight": "bold"}, }
            )
        return selected_option

    def render_page(self, selected_option: str):
        """Renders the sub-page based on the menu selection."""
        if selected_option == 'Dashboard':
            dashboard.app(self.user_data_service)
        elif selected_option == 'Verify Users':
            verify_users.app(self.user_data_service)
        elif selected_option == 'RAG Management':  # Sesuaikan dengan nama di options
            rag.app(self.rag_service)

    def render(self):
        """Renders the complete Admin Page."""
        # Check session validity first
        if not ensure_valid_session():
            return

        self.configure_page()
        initialize_session_state()
        self.load_css("static/css/style.css")  # Pastikan path CSS benar

        # Display session warning if needed
        display_session_warning()

        # --- Authorization Check for Admin Role ---
        if "role" not in st.session_state or st.session_state.role != "Admin":
            st.error("🚫 You are not authorized to view this page.")
            st.info(
                f"Your current role: {st.session_state.get('role', 'Unknown')}")
            st.page_link("pages/1 Home Page.py", label="Go to Home", icon="🏠")
            return  # Stop rendering further
        # --- End Check ---

        # Render sidebar and selected page content if authorized
        selected_option = self.render_sidebar()
        self.render_page(selected_option)

import streamlit as st

# Import with error handling
try:
    from core import initialize_session_state
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please ensure all required modules are installed and accessible.")
    st.stop()

from features.admin.controller import AdminPage

initialize_session_state()

# Check if user is authenticated and has admin role
if not st.session_state.get("username") or st.session_state.get("signout", True):
    st.error("Please login to access this page.")
    st.switch_page("Main_Page.py")
    st.stop()

user_role = st.session_state.get("role", "")
if user_role.lower() != "admin":
    st.error("Access denied. Admin privileges required.")
    st.switch_page("pages/1 Home Page.py")
    st.stop()

# Ambil service dari session state
user_service = st.session_state.get("user_service")
user_data_service = st.session_state.get("user_data_service")
rag_service = st.session_state.get("rag_service")

admin_page = AdminPage(
    user_service=user_service,
    user_data_service=user_data_service,
    rag_service=rag_service
)

# Render halaman AdminPage
admin_page.render()

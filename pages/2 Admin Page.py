import streamlit as st

# Import with error handling
try:
    from core import initialize_session_state
    from core.utils.session_manager import ensure_valid_session, display_session_warning
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please ensure all required modules are installed and accessible.")
    st.stop()

from features.admin.controller import AdminPage

initialize_session_state()

# Ensure valid session - this handles all session checks and redirects
if not ensure_valid_session():
    st.stop()

# Check admin role specifically
user_role = st.session_state.get("role", "")
if user_role.lower() != "admin":
    st.error("🚫 Access denied. Admin privileges required.")
    st.info("Please contact administrator if you believe this is an error.")
    st.switch_page("pages/1 Home Page.py")
    st.stop()

# Display session warning if needed
display_session_warning()

# Display session info in sidebar
with st.sidebar:
    username = st.session_state.get("username", "")
    remaining_time = st.session_state.get("session_remaining_time", "")
    if username and remaining_time:
        st.info(f"👤 {username}")
        st.info(f"⏰ Session: {remaining_time}")

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

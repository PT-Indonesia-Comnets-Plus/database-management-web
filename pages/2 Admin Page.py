from features.admin.controller import AdminPage
import streamlit as st
from core import initialize_session_state

initialize_session_state()
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

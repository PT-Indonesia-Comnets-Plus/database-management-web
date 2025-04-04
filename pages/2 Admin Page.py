from page_logic.admin_page_logic import AdminPage
import streamlit as st
from utils.firebase_config import get_firebase_app
if "fs" not in st.session_state:
    st.session_state.fs, st.session_state.auth = get_firebase_app()
# Inisialisasi HomePage
home_page = AdminPage(st.session_state.fs, st.session_state.auth)

# Render halaman Home Page
home_page.render()

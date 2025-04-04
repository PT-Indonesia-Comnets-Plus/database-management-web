from page_logic.admin_page_logic import AdminPage
from utils import initialize_session_state
import streamlit as st

# Inisialisasi session state
initialize_session_state()

# Periksa apakah pengguna memiliki role "Admin"
admin_page = AdminPage(st.session_state.fs,
                       st.session_state.auth, st.session_state.fs_config)

# Render halaman AdminPage
admin_page.render()

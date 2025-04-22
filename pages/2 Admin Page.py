from features.admin.controller import AdminPage
from utils import initialize_session_state
import streamlit as st
from models.EmailService import EmailService
from models.UserService import UserService

# Inisialisasi session state
initialize_session_state()
email_service = EmailService(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    smtp_username="your_email@gmail.com",
    smtp_password="your_email_password"
)

# Inisialisasi UserService
user_service = UserService(
    firestore=st.session_state.fs,
    auth=st.session_state.auth,
    firebase_api=st.session_state.fs_config,
    email_service=email_service
)

# Periksa apakah pengguna memiliki role "Admin"
admin_page = AdminPage(st.session_state.fs,
                       st.session_state.auth, st.session_state.fs_config)

# Render halaman AdminPage
admin_page.render()

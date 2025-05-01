import streamlit as st
from PIL import Image
from io import BytesIO
import base64
from core.services.UserService import UserService
from core.services.EmailService import EmailService
from core import initialize_session_state
import os
from PIL import ImageOps

st.logo("static/image/logo_iconplus.png", size="large")
try:
    logo = Image.open("static/image/icon.png").resize((40, 50))
    logo_with_padding = ImageOps.expand(
        logo, border=8, fill=(255, 255, 255, 0)
    )
    st.set_page_config(page_title="Main Page",
                       page_icon=logo_with_padding)
except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
    pass
initialize_session_state()
fs = st.session_state.fs
auth = st.session_state.auth
fs_config = st.session_state.fs_config

# Inisialisasi EmailService
email_service = EmailService(
    smtp_server=st.secrets['smtp']["server"],
    smtp_port=st.secrets['smtp']["port"],
    smtp_username=st.secrets['smtp']["username"],
    smtp_password=st.secrets['smtp']["password"]
)

# Inisialisasi UserService
user_service = UserService(
    fs, auth, fs_config, email_service
)


# Load CSS
if os.path.exists('static/css/style.css'):
    with open('static/css/style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def image_to_base64(image: Image.Image) -> str:
    """
    Mengonversi gambar ke format base64 untuk ditampilkan di Streamlit.
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


# Tampilkan logo di halaman utama
logo_home_path = "static/image/logo_Iconnet.png"
if os.path.exists(logo_home_path):
    logo_home = Image.open(logo_home_path)
    logo_base64 = image_to_base64(logo_home)
    st.markdown(
        f"""
        <div style="text-align: center; padding: 0px 0;">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="width: 100%; max-width: 400px;">
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<h1 style='text-align: center;'>Welcome!</h1>",
            unsafe_allow_html=True)

# Login atau Signup
if st.session_state.get("signout", True):
    choice = st.selectbox("Login/Signup", ["Login", "Sign up"])
    if choice == "Login":
        email = st.text_input("Email", key="login_email")
        password = st.text_input(
            "Password", type="password", key="login_password")
        st.button("Login", on_click=lambda: user_service.login(email, password))
    else:
        username = st.text_input("Username", key="signup_username")
        email = st.text_input("Email Address", key="signup_email")
        password = st.text_input(
            "Password", type="password", key="signup_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="signup_confirm_password")
        st.button("Sign Up", on_click=lambda: user_service.signup(username, email, password,
                                                                  confirm_password, role="Employee"))
else:
    st.markdown(
        f"<h2 style='text-align: left;'>Welcome back, {st.session_state.username}!</h2>", unsafe_allow_html=True)
    st.text(f"Email: {st.session_state.useremail}")
    st.text(f"Role: {st.session_state.role}")
    st.button("Sign Out", on_click=lambda: user_service.logout())

# Tambahkan styling untuk input
st.markdown(
    """
    <style>
    input[data-testid="stTextInput"][aria-label="Email"] {
        color: white;
    }
    input[data-testid="stTextInput"][aria-label="Password"] {
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

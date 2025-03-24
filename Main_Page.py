import streamlit as st
from PIL import Image
from io import BytesIO
import base64
from dotenv import load_dotenv
from utils.account import login, logout, signup
from utils.cookies import load_cookie_to_session
import os
from utils.firebase_config import get_firebase_app

# Set page configuration
logo_path = os.path.join("image", "icon.png")
logo = Image.open(logo_path)
try:
    st.set_page_config(
        page_title="Welcome to Iconnet Dashboard", page_icon=logo)
except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
    pass

# Initialize session state attributes
if "username" not in st.session_state:
    load_cookie_to_session(st.session_state)

if "fs" not in st.session_state:
    st.session_state.fs = get_firebase_app()
fs = st.session_state.fs

load_dotenv()

# Load sidebar logo
sidebar_logo_path = "image/logo_iconplus.png"
sidebar_logo = Image.open(sidebar_logo_path)
st.sidebar.image(sidebar_logo, caption="")

# Load CSS
if os.path.exists('style.css'):
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


# Load and display home logo
logo_home_path = "image/logo_Iconnet.png"
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


if st.session_state.signout:
    choice = st.selectbox("Login/Signup", ["Login", "Sign up"])
    if choice == "Login":
        st.text_input("Email", key="login_email")
        st.text_input("Password", type="password", key="login_password")
        st.button("Login", on_click=lambda: login(
            fs, st.session_state.login_email, st.session_state.login_password))
    else:
        st.text_input("Username", key="signup_username")
        st.text_input("Email Address", key="signup_email")
        st.text_input("Password", type="password", key="signup_password")
        st.text_input("Confirm Password", type="password",
                      key="signup_confirm_password")
        if st.button("Sign Up"):
            signup(fs, st.session_state.signup_username, st.session_state.signup_email,
                   st.session_state.signup_password, st.session_state.signup_confirm_password, role="Employe")
else:
    st.markdown(
        f"<h2 style='text-align: left;'>Welcome back, {st.session_state.username}!</h2>", unsafe_allow_html=True)
    st.text(f"Email: {st.session_state.useremail}")
    st.text(f"Role: {st.session_state.role}")
    st.button("Sign Out", on_click=lambda: logout(fs))


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

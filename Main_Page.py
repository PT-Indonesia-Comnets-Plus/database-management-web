import streamlit as st
from PIL import Image
from io import BytesIO
import base64
from dotenv import load_dotenv
from utils.firebase_config import fs
from utils.account import login, logout, send_verification_email
from utils.cookies import save_user_to_cookie, load_cookie_to_session, clear_user_cookie
from firebase_admin import auth
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
if 'signout' not in st.session_state:
    st.session_state.signout = True
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'useremail' not in st.session_state:
    st.session_state.useremail = ""
if 'role' not in st.session_state:
    st.session_state.role = ""
if 'db' not in st.session_state:
    st.session_state.db = get_firebase_app()

try:
    load_cookie_to_session(st.session_state)
except RuntimeError:
    st.stop()

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

# Welcome text
st.markdown("<h1 style='text-align: center;'>Welcome!</h1>",
            unsafe_allow_html=True)


def handle_login():
    email = st.session_state.login_email
    password = st.session_state.login_password
    login(email, password)


def handle_signup():
    username = st.session_state.signup_username
    email = st.session_state.signup_email
    password = st.session_state.signup_password
    confirm_password = st.session_state.signup_confirm_password
    role = "Employe"
    if password != confirm_password:
        st.error("Passwords do not match. Please try again.")
    else:
        try:
            user = auth.create_user(
                email=email, password=password, uid=username)
            user_data = {"name": username, "email": email,
                         "role": role, "status": "Pending"}

            fs.collection("users").document(user.uid).set(user_data)
            send_verification_email(email)
            st.success(
                "Account created successfully! Please verify your email.")
            st.balloons()
        except Exception as e:
            st.error(f"Error creating account: {e}")


if st.session_state.signout:
    choice = st.selectbox("Login/Signup", ["Login", "Sign up"])

    if choice == "Login":
        st.text_input("Email", key="login_email")
        st.text_input("Password", type="password", key="login_password")
        st.button("Login", on_click=handle_login)
    else:
        st.text_input("Username", key="signup_username")
        st.text_input("Email Address", key="signup_email")
        st.text_input("Password", type="password", key="signup_password")
        st.text_input("Confirm Password", type="password",
                      key="signup_confirm_password")
        st.button("Create my account", on_click=handle_signup)
else:
    st.markdown(
        f"<h2 style='text-align: left;'>Welcome back, {st.session_state.username}!</h2>", unsafe_allow_html=True)
    st.text(f"Email: {st.session_state.useremail}")
    st.text(f"Role: {st.session_state.role}")
    if st.button('Sign Out'):
        logout()

# Custom CSS to change the color of specific input fields
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

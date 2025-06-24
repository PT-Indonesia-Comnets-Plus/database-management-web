"""
Cookie/Session Management for ICONNET Application
Adapted from prototyping reference for Streamlit Cloud compatibility - EXACT PATTERN
"""

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize cookie manager EXACTLY like prototyping but for ICONNET
password = os.environ.get('COOKIE_PASSWORD', 'iconnet_secure_key_2024')

cookies = EncryptedCookieManager(
    prefix="iconnet_",
    password=password
)

# Pastikan cookies siap digunakan (EXACTLY like prototyping)
if not cookies.ready():
    logger.error("Cookies manager is not ready.")
    # Don't raise RuntimeError, let Streamlit handle the rerun
    st.stop()


# Backward-compatible function signatures for existing code (Following prototyping pattern)
def save_user_to_cookie(username, email, role):
    """
    Save user data to cookies and session state.
    Follows prototyping pattern but adapted for ICONNET (no store_name).

    Args:
        username (str): Username
        email (str): User email  
        role (str): User role
    """
    # Save to cookies (exactly like prototyping)
    cookies["username"] = username
    cookies["email"] = email
    cookies["role"] = role
    cookies["signout"] = "False"  # String like prototyping
    cookies.save()

    # Also save to session state with ICONNET mapping
    st.session_state.username = username
    st.session_state.useremail = email  # ICONNET uses 'useremail'
    st.session_state.role = role
    st.session_state.signout = False  # Boolean in session state

    logger.info(f"User session saved for user: {username}")
    return True


def clear_user_cookie():
    """
    Clear user session data from cookies and session state.
    Follows prototyping pattern but adapted for ICONNET.
    """
    cookies["username"] = ""
    cookies["email"] = ""
    cookies["role"] = ""
    cookies["signout"] = "True"  # String like prototyping
    cookies.save()

    # Clear from session state (ICONNET keys)
    session_keys_to_clear = [
        'username', 'useremail', 'role', 'signout',
        'messages', 'thread_id'
    ]

    for key in session_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Set signout to True explicitly
    st.session_state.signout = True

    logger.info("User session cleared")


def load_cookie_to_session(session_state):
    """
    Load user data from cookies to session state.
    Follows prototyping pattern but adapted for ICONNET mapping.

    Args:
        session_state: Streamlit session state object to load data into

    Returns:
        bool: True if session data was loaded, False otherwise
    """
    # Load from cookies with prototyping pattern
    username = cookies.get("username", "")
    email = cookies.get("email", "")
    role = cookies.get("role", "")
    signout = cookies.get("signout", "True") == "True"  # String to boolean

    # Only load if we have valid user data
    if username and email and role:
        session_state.username = username
        session_state.useremail = email  # ICONNET uses 'useremail'
        session_state.role = role
        session_state.signout = signout
        logger.info(
            f"User session loaded from cookies for user: {username}")
        return True

    return False


def is_user_logged_in():
    """
    Check if user is currently logged in.
    Following ICONNET pattern.

    Returns:
        bool: True if user is logged in, False otherwise
    """
    # Check session state with ICONNET keys
    username_exists = bool(st.session_state.get("username", "").strip())
    is_signed_out = st.session_state.get("signout", True)

    # User is authenticated if username exists and not signed out
    return username_exists and not is_signed_out

import streamlit as st
from .cookies import load_cookie_to_session
from .firebase_config import get_firebase_app
from .database import connect_db


def initialize_session_state():
    """Inisialisasi atribut session_state jika belum ada."""
    if "username" not in st.session_state:
        load_cookie_to_session(st.session_state)

    if "db_connection" not in st.session_state:
        try:
            st.session_state.db, st.session_state.storage = connect_db()
        except Exception as e:
            st.error(f"Failed to connect to the database: {e}")

    if "fs" not in st.session_state or "auth" not in st.session_state:
        try:
            st.session_state.fs, st.session_state.auth, st.session_state.fs_config = get_firebase_app()
        except Exception as e:
            st.error(f"Failed to initialize Firestore: {e}")

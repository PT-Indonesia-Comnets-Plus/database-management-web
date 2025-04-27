# core/__init__.py
import streamlit as st
from utils.cookies import load_cookie_to_session
from .firebase_config import get_firebase_app
from .database import connect_db  # Fungsi yang mengembalikan pool


def initialize_session_state():
    """Inisialisasi atribut session_state jika belum ada."""
    if "username" not in st.session_state:
        load_cookie_to_session(st.session_state)
    if "db" not in st.session_state:
        try:
            st.session_state.db, st.session_state.storage = connect_db()
            if st.session_state.db is None:
                st.error("Inisialisasi DB Pool gagal.")
        except Exception as e:
            st.error(f"Failed to connect to the database pool: {e}")

    if "fs" not in st.session_state or "auth" not in st.session_state:
        try:
            st.session_state.fs, st.session_state.auth, st.session_state.fs_config = get_firebase_app()
        except Exception as e:
            st.error(f"Failed to initialize Firestore: {e}")

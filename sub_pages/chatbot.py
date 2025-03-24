import streamlit as st
from utils.database import connect_db


def app():
    st.title("Chatbot")

    # Initialize session state for db
    if 'db' not in st.session_state:
        st.session_state.db = None

    # Connect to the database if not already connected
    if st.session_state.db is None:
        st.session_state.db = connect_db()

    db = st.session_state.db

    st.write("Chatbot is under construction.")

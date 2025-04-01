import streamlit as st
from utils.database import connect_db


def app():
    st.title("Search")
    if "db" not in st.session_state:
        st.session_state.db = connect_db()
    db = st.session_state.db
    st.write("Search is under construction.")

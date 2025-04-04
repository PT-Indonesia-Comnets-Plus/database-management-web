import streamlit as st
from utils.database import connect_db


def app():
    st.title("Search")
    db = st.session_state.db
    st.write("Search is under construction.")

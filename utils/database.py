import psycopg2
import streamlit as st

DB_HOST = st.secrets["database"]["DB_HOST"]
DB_NAME = st.secrets["database"]["DB_NAME"]
DB_USER = st.secrets["database"]["DB_USER"]
DB_PASSWORD = st.secrets["database"]["DB_PASSWORD"]
DB_PORT = st.secrets["database"]["DB_PORT"]


def connect_db():
    """Create a connection to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn

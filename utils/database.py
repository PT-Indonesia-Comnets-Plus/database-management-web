import psycopg2
import streamlit as st
from supabase import create_client

DB_HOST = st.secrets["database"]["DB_HOST"]
DB_NAME = st.secrets["database"]["DB_NAME"]
DB_USER = st.secrets["database"]["DB_USER"]
DB_PASSWORD = st.secrets["database"]["DB_PASSWORD"]
DB_PORT = st.secrets["database"]["DB_PORT"]

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["service_role_key"]


@st.cache_resource
def connect_db():
    """Create a connection to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return conn, supabase

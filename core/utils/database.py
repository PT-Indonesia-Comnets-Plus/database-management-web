# core/database.py

# --- Perbaikan Import ---
import psycopg2
from psycopg2 import pool  # <-- Tambahkan import spesifik untuk pool
# -----------------------

import streamlit as st
from supabase import create_client

# Ambil secrets seperti sebelumnya
DB_HOST = st.secrets["database"]["DB_HOST"]
DB_NAME = st.secrets["database"]["DB_NAME"]
DB_USER = st.secrets["database"]["DB_USER"]
DB_PASSWORD = st.secrets["database"]["DB_PASSWORD"]
DB_PORT = st.secrets["database"]["DB_PORT"]

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["service_role_key"]


@st.cache_resource
def connect_db():
    """Membuat connection pool psycopg2."""
    try:
        # --- Perbaikan Pembuatan Pool ---
        # Gunakan 'pool' yang sudah diimpor, bukan 'psycopg2.pool'
        db_pool = pool.SimpleConnectionPool(
            1, 5,  # minconn=1, maxconn=5 (sesuaikan)
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        # -------------------------------

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return db_pool, supabase
    except Exception as e:
        return None, None

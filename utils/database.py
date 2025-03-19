import psycopg2
import asyncpg
import asyncio
import streamlit as st

DB_HOST = st.secrets["database"]["DB_HOST"]
DB_NAME = st.secrets["database"]["DB_NAME"]
DB_USER = st.secrets["database"]["DB_USER"]
DB_PASSWORD = st.secrets["database"]["DB_PASSWORD"]
DB_PORT = st.secrets["database"]["DB_PORT"]


async def connect_db():
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

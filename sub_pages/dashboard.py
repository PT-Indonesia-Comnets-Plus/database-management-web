import streamlit as st
import asyncio
from utils.database import connect_db
import pandas as pd


async def load_data():
    conn = await connect_db()
    if conn:
        try:
            rows = await conn.fetch("SELECT * FROM data_aset LIMIT 10")
            colnames = [key for key in rows[0].keys()] if rows else []
            df = pd.DataFrame(rows, columns=colnames)
            return df
        except Exception as e:
            st.error(f"Query Error: {e}")
            return None
        finally:
            await conn.close()
    else:
        st.warning("Koneksi Database Gagal!")
        return None


def app():

    st.title("Management System Iconnet:")

    # Initialize session state for db
    if 'db' not in st.session_state:
        st.session_state.db = None

    # Connect to the database if not already connected
    if st.session_state.db is None:
        st.session_state.db = asyncio.run(connect_db())

    db = st.session_state.db

    # Load data and store in session state if not already loaded
    if 'df' not in st.session_state:
        st.session_state.df = asyncio.run(load_data())

    df = st.session_state.df
    st.subheader("Welcome to Iconnet Management System")
    st.dataframe(df)

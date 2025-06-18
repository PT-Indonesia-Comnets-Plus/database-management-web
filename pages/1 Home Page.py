# pages/1 Home Page.py
from core import initialize_session_state
from features.home.controller import HomePage
import streamlit as st
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Panggil inisialisasi di awal untuk memastikan semua service ada
initialize_session_state()

# Ambil dependensi yang dibutuhkan oleh HomePage controller
asset_data_service = st.session_state.get("asset_data_service")
db_pool = st.session_state.get("db")

# Periksa apakah dependensi berhasil dimuat
if asset_data_service is None or db_pool is None:
    missing = []
    if asset_data_service is None:
        missing.append("Asset Data Service")
    if db_pool is None:
        missing.append("Database Pool")
    st.error(
        f"Failed to initialize required services ({', '.join(missing)}). Home page cannot be rendered.")
    st.stop()

# Inisialisasi HomePage dengan dependensi
home_page = HomePage(asset_data_service=asset_data_service, db_pool=db_pool)

# Render halaman Home Page
home_page.render()

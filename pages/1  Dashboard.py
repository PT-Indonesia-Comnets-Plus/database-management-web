import streamlit as st
from PIL import Image, ImageOps
from utils.database import connect_db
from utils.cookies import load_cookie_to_session
import os
import pandas as pd
import asyncio

# Load data from cookies
try:
    load_cookie_to_session(st.session_state)
except RuntimeError:
    st.stop()

logo_path = os.path.join("image", "icon.png")
logo = Image.open(logo_path)

logo_resized = logo.resize((40, 50))
padding = 8
new_size = (logo_resized.width + 2 * padding,
            logo_resized.height + 2 * padding)
logo_with_padding = ImageOps.expand(logo_resized, border=padding, fill=(
    255, 255, 255, 0))

try:
    st.set_page_config(page_title="Dashboard Page",
                       page_icon=logo_with_padding)
except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
    pass


async def load_data():
    conn = await connect_db()
    if conn:
        try:
            # Query ambil data
            rows = await conn.fetch("SELECT * FROM datekasetall LIMIT 10")

            # Ambil nama kolom dari hasil query
            colnames = [key for key in rows[0].keys()] if rows else []

            # Masukin data ke Pandas DataFrame
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

df = asyncio.run(load_data())
if df is not None:
    # Tampilkan tabel di Streamlit
    st.dataframe(df)

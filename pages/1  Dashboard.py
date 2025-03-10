import streamlit as st
from PIL import Image
from utils.database import connect_db
from utils.cookies import load_cookie_to_session
import os

# Load data from cookies
username, useremail, role, signout = load_cookie_to_session()

# Set page configuration
logo_path = os.path.join("image", "icon.png")
logo = Image.open(logo_path)
st.set_page_config(page_title="Dashboard", page_icon=logo)

if role == "Employe" and not signout:
    st.title("📊 Dashboard Data Aset")

    conn = connect_db()

    if conn:
        cur = conn.cursor()

        try:
            # Query ambil data
            cur.execute("SELECT * FROM datekasetall")
            rows = cur.fetchall()

            # Ambil nama kolom biar tabel rapih
            colnames = [desc[0] for desc in cur.description]

            # Masukin data ke Pandas DataFrame
            df = pd.DataFrame(rows, columns=colnames)

            # Tampilkan tabel di Streamlit
            st.dataframe(df)

        except Exception as e:
            st.error(f"Query Error: {e}")

        finally:
            cur.close()
            conn.close()
    else:
        st.warning("Koneksi Database Gagal!")
else:
    st.error("Please log in as Employe to access this page.")

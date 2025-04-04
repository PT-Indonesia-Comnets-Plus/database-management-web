import streamlit as st
import pandas as pd
from utils.database import connect_db


def load_data(db):
    """Load data aset dari database."""
    conn = db
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM data_aset LIMIT 10")
                rows = cur.fetchall()
                colnames = [desc[0]
                            for desc in cur.description]
                df = pd.DataFrame(rows, columns=colnames)
                return df
        except Exception as e:
            st.error(f"Query Error: {e}")
            return None
        finally:
            conn.close()
    else:
        st.warning("Koneksi Database Gagal!")
        return None


def app():
    st.title("Management System Iconnet")
    if "db" not in st.session_state:
        st.session_state.db = connect_db()
    db = st.session_state.db
    # Load data hanya sekali dan simpan di session state
    if "df" not in st.session_state:
        st.session_state.df = load_data(db)

    df = st.session_state.df
    if df is not None:
        st.subheader("Welcome to Iconnet Management System")
        st.dataframe(df)
    else:
        st.warning("Tidak ada data yang bisa ditampilkan.")


if __name__ == "__main__":
    app()

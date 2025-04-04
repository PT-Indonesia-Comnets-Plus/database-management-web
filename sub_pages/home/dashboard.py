import streamlit as st
import pandas as pd


@st.cache_resource
def load_data(_db):
    """Load data aset dari database."""
    conn = _db
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM data_aset LIMIT 10")
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description]
                df = pd.DataFrame(rows, columns=colnames)
                return df
        except Exception as e:
            st.error(f"Query Error: {e}")
            return None
    else:
        st.warning("Koneksi Database Gagal!")
        return None


def app():

    st.title("Management System Iconnet")
    # Gunakan koneksi database dari session_state

    # Load data hanya sekali dan simpan di session state
    if "df" not in st.session_state:
        st.session_state.df = load_data(st.session_state.db)

    df = st.session_state.df
    if df is not None:
        st.subheader("Welcome to Iconnet Management System")
        st.dataframe(df)
    else:
        st.warning("Tidak ada data yang bisa ditampilkan.")


if __name__ == "__main__":
    app()

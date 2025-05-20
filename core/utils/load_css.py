import os
import streamlit as st


def load_custom_css(path: str) -> None:
    """
    Memuat custom CSS dari file yang ditentukan.

    Args:
        path (str): Path ke file CSS.
    """
    if os.path.exists(path):
        try:
            with open(path) as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Gagal memuat CSS: {e}")

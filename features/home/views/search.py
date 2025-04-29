# features/home/views/search.py
import streamlit as st
from core.services.AssetDataService import AssetDataService  # Import service


def app(asset_data_service: AssetDataService):
    """
    Provides an interface to search for specific assets in the database.
    (Currently a placeholder).

    Args:
        asset_data_service: An instance of AssetDataService to perform searches.
    """
    st.title("🔍 Search Assets")
    st.write("Search functionality is under construction.")

    # Contoh implementasi sederhana:
    search_term = st.text_input("Search by FAT ID (example)")
    if st.button("Search"):
        if search_term:
            with st.spinner("Searching..."):
                results_df = asset_data_service.search_assets(
                    column_name="fat_id", value=search_term)
            if results_df is not None and not results_df.empty:
                st.dataframe(results_df, hide_index=True)
            elif results_df is not None:
                st.info("No matching assets found.")
            # Error ditangani service
        else:
            st.warning("Please enter a search term.")

# Hapus `if __name__ == "__main__":` jika ada

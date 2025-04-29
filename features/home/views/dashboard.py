# features/home/views/dashboard.py
import streamlit as st
import pandas as pd
from core.services.AssetDataService import AssetDataService  # Import service


def app(asset_data_service: AssetDataService):
    """
    Displays the main dashboard with a sample of asset data.

    Args:
        asset_data_service: An instance of AssetDataService to load data.
    """
    st.title("📊 Asset Dashboard")
    st.markdown("Overview of the ICONNET asset management system.")

    # Load data using the service
    with st.spinner("Loading asset data..."):
        df = asset_data_service.load_all_assets(
            limit=50)  # Load limited data for dashboard

    if df is not None and not df.empty:
        st.subheader("Recent Asset Data Sample")
        st.dataframe(df, use_container_width=True, hide_index=True)
    elif df is not None and df.empty:
        st.info("No asset data found in the database.")
    else:
        # Error message already shown by the service
        st.warning("Could not display asset data.")

# Hapus `if __name__ == "__main__":` jika ada

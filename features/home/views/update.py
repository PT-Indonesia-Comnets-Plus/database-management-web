# features/home/views/update.py
import streamlit as st
import pandas as pd
# Import datetime jika diperlukan untuk konversi tipe
from datetime import date, datetime
from copy import deepcopy
from core.services.AssetDataService import AssetDataService  # Import service

# --- Fungsi Helper untuk UI ---


def display_search_results(results_key: str):
    """Displays search results from session_state if available."""
    if results_key in st.session_state and not st.session_state[results_key].empty:
        st.subheader("Search Results")
        st.dataframe(st.session_state[results_key],
                     hide_index=True, use_container_width=True)
        return True
    return False

# --- Fungsi untuk Bagian Edit ---


def search_for_edit(asset_data_service: AssetDataService):
    """Handles the search UI for the edit process."""
    st.subheader("1. Search Record to Edit")
    col1, col2 = st.columns([1, 3])
    with col1:
        search_option_map = {"FAT ID": "fat_id",
                             "FDT ID": "fdt_id", "OLT Hostname": "hostname_olt"}
        search_display = st.selectbox("Search by", list(
            search_option_map.keys()), key="edit_search_option")
        search_column = search_option_map[search_display]
    with col2:
        search_value = st.text_input("Search value", key="edit_search_value")

    if st.button("Search 🔍", key="edit_search_button"):
        # Clear previous edit state
        keys_to_clear = ["edit_search_results", "edit_selected_record_idx", "edit_selected_record_data",
                         "edit_original_record_data", "edit_show_confirmation", "edit_changes_to_confirm"]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

        if not search_value:
            st.warning("Please enter a search value.")
        else:
            with st.spinner("Searching..."):
                df = asset_data_service.search_assets(
                    column_name=search_column, value=search_value)
            if df is not None and not df.empty:
                st.session_state.edit_search_results = df
                st.success(f"Found {len(df)} record(s).")
            elif df is not None:
                st.info("No matching records found.")
            # Error handled by service

    display_search_results("edit_search_results")


def select_for_edit(asset_data_service: AssetDataService):
    """Handles the record selection UI for editing."""
    if "edit_search_results" not in st.session_state or st.session_state.edit_search_results.empty:
        return

    st.subheader("2. Select Record to Edit")
    df = st.session_state.edit_search_results
    record_options = {
        f"FAT ID: {row['fat_id']} (Index: {idx})": idx for idx, row in df.iterrows()}

    selected_display = st.selectbox("Choose record:", list(record_options.keys()),
                                    key="edit_record_selector", index=None, placeholder="Select a record...")

    if selected_display:
        selected_idx = record_options[selected_display]
        st.session_state.edit_selected_record_idx = selected_idx  # Simpan index terpilih
        selected_fatid = df.loc[selected_idx, 'fat_id']
        st.info(
            f"Record with FAT ID '{selected_fatid}' selected. Loading latest data for editing...")

        # Fetch latest data before editing
        with st.spinner("Fetching latest record data..."):
            latest_df = asset_data_service.search_assets(
                column_name="fat_id", value=selected_fatid)

        if latest_df is not None and not latest_df.empty:
            record_dict = latest_df.iloc[0].to_dict()
            st.session_state.edit_selected_record_data = record_dict
            st.session_state.edit_original_record_data = deepcopy(record_dict)
            st.success("Latest data loaded. Proceed to edit form below.")
        else:
            st.error("Failed to reload the selected record from the database.")
            st.session_state.pop("edit_selected_record_idx", None)
            st.session_state.pop("edit_selected_record_data", None)
            st.session_state.pop("edit_original_record_data", None)


def display_edit_form_and_confirm(asset_data_service: AssetDataService):
    """Displays the edit form and handles update logic including confirmation."""
    if "edit_selected_record_data" not in st.session_state:
        return

    st.subheader("3. Edit Record Details")
    record_data = st.session_state.edit_selected_record_data
    original_data = st.session_state.edit_original_record_data
    fat_id_display = record_data.get("fat_id", "N/A")

    with st.form(key="edit_asset_form", clear_on_submit=False):
        st.write(f"**Editing FAT ID:** {fat_id_display}")
        edited_values = {}

        # --- Expander 1: General Information (Additional Info) ---
        with st.expander("General Information (Additional Info)"):
            edited_values["pa"] = st.text_input(
                "PA", value=record_data.get("pa", ""), key="edit_pa")
            tanggal_rfs_val = record_data.get("tanggal_rfs")
            if isinstance(tanggal_rfs_val, str):
                try:
                    tanggal_rfs_val = datetime.strptime(
                        tanggal_rfs_val, '%Y-%m-%d').date()
                except:
                    tanggal_rfs_val = date.today()
            elif not isinstance(tanggal_rfs_val, date):
                tanggal_rfs_val = date.today()
            edited_values["tanggal_rfs"] = st.date_input(
                "Tanggal RFS", value=tanggal_rfs_val, key="edit_tanggal_rfs")
            edited_values["mitra"] = st.text_input(
                "Mitra", value=record_data.get("mitra", ""), key="edit_mitra")
            edited_values["kategori"] = st.text_input(
                "Kategori", value=record_data.get("kategori", ""), key="edit_kategori")
            edited_values["sumber_datek"] = st.text_input(
                "Sumber Datek", value=record_data.get("sumber_datek", ""), key="edit_sumber_datek")

        # --- Expander 2: OLT Information (User Terminals) ---
        with st.expander("OLT Information (User Terminals)"):
            edited_values["hostname_olt"] = st.text_input(
                "Hostname OLT", value=record_data.get("hostname_olt", ""), key="edit_hostname_olt")
            edited_values["latitude_olt"] = st.number_input(
                "Latitude OLT", value=record_data.get("latitude_olt"), format="%.8f", key="edit_latitude_olt")
            edited_values["longitude_olt"] = st.number_input(
                "Longitude OLT", value=record_data.get("longitude_olt"), format="%.8f", key="edit_longitude_olt")
            edited_values["brand_olt"] = st.text_input(
                "Brand OLT", value=record_data.get("brand_olt", ""), key="edit_brand_olt")
            edited_values["type_olt"] = st.text_input(
                "Type OLT", value=record_data.get("type_olt", ""), key="edit_type_olt")
            edited_values["kapasitas_olt"] = st.number_input(
                "Kapasitas OLT", min_value=0, value=int(record_data.get("kapasitas_olt", 0) or 0), step=1, key="edit_kapasitas_olt")
            edited_values["kapasitas_port_olt"] = st.number_input(
                "Kapasitas Port OLT", min_value=0, value=int(record_data.get("kapasitas_port_olt", 0) or 0), step=1, key="edit_kapasitas_port_olt")
            edited_values["olt_port"] = st.number_input(
                "OLT Port", min_value=0, value=int(record_data.get("olt_port", 0) or 0), step=1, key="edit_olt_port")
            edited_values["olt"] = st.text_input(
                "OLT", value=record_data.get("olt", ""), key="edit_olt")
            edited_values["interface_olt"] = st.text_input(
                "Interface OLT", value=record_data.get("interface_olt", ""), key="edit_interface_olt")

        # --- Expander 3: FDT Information ---
        with st.expander("FDT Information"):
            edited_values["fdt_id"] = st.text_input(
                "FDT ID", value=record_data.get("fdt_id", ""), key="edit_fdt_id")
            edited_values["status_osp_amarta_fdt"] = st.text_input(
                "Status OSP Amarta FDT", value=record_data.get("status_osp_amarta_fdt", ""), key="edit_status_osp_amarta_fdt")
            edited_values["jumlah_splitter_fdt"] = st.number_input(
                "Jumlah Splitter FDT", min_value=0, value=int(record_data.get("jumlah_splitter_fdt", 0) or 0), step=1, key="edit_jumlah_splitter_fdt")
            edited_values["kapasitas_splitter_fdt"] = st.number_input(
                "Kapasitas Splitter FDT", min_value=0, value=int(record_data.get("kapasitas_splitter_fdt", 0) or 0), step=1, key="edit_kapasitas_splitter_fdt")

        # --- Expander 4: FAT Information ---
        with st.expander("FAT Information"):
            edited_values["jumlah_splitter_fat"] = st.number_input(
                "Jumlah Splitter FAT", min_value=0, value=int(record_data.get("jumlah_splitter_fat", 0) or 0), step=1, key="edit_jumlah_splitter_fat")
            edited_values["kapasitas_splitter_fat"] = st.number_input(
                "Kapasitas Splitter FAT", min_value=0, value=int(record_data.get("kapasitas_splitter_fat", 0) or 0), step=1, key="edit_kapasitas_splitter_fat")
            edited_values["latitude_fat"] = st.number_input(
                "Latitude FAT", value=record_data.get("latitude_fat"), format="%.8f", key="edit_latitude_fat")
            edited_values["longitude_fat"] = st.number_input(
                "Longitude FAT", value=record_data.get("longitude_fat"), format="%.8f", key="edit_longitude_fat")

        # --- Expander 5: Cluster Information ---
        with st.expander("Cluster Information"):
            edited_values["latitude_cluster"] = st.number_input(
                "Latitude Cluster", value=record_data.get("latitude_cluster"), format="%.8f", key="edit_latitude_cluster")
            edited_values["longitude_cluster"] = st.number_input(
                "Longitude Cluster", value=record_data.get("longitude_cluster"), format="%.8f", key="edit_longitude_cluster")
            edited_values["area_kp"] = st.text_input(
                "Area KP", value=record_data.get("area_kp", ""), key="edit_area_kp")
            edited_values["kota_kab"] = st.text_input(
                "Kota/Kabupaten", value=record_data.get("kota_kab", ""), key="edit_kota_kab")
            edited_values["kecamatan"] = st.text_input(
                "Kecamatan", value=record_data.get("kecamatan", ""), key="edit_kecamatan")
            edited_values["kelurahan"] = st.text_input(
                "Kelurahan", value=record_data.get("kelurahan", ""), key="edit_kelurahan")

        # --- Expander 6: Home Connecteds (HC) Information ---
        with st.expander("Home Connecteds (HC) Information"):
            edited_values["hc_old"] = st.number_input(
                "HC OLD", min_value=0, value=int(record_data.get("hc_old", 0) or 0), step=1, key="edit_hc_old")
            edited_values["hc_icrm"] = st.number_input(
                "HC iCRM", min_value=0, value=int(record_data.get("hc_icrm", 0) or 0), step=1, key="edit_hc_icrm")
            edited_values["total_hc"] = st.number_input(
                "Total HC", min_value=0, value=int(record_data.get("total_hc", 0) or 0), step=1, key="edit_total_hc")

        # --- Expander 7: Dokumentasi Information ---
        with st.expander("Dokumentasi Information"):
            edited_values["status_osp_amarta_fat"] = st.text_input(
                "Status OSP Amarta FAT", value=record_data.get("status_osp_amarta_fat", ""), key="edit_status_osp_amarta_fat")
            edited_values["link_dokumen_feeder"] = st.text_input(
                "Link Dokumen Feeder", value=record_data.get("link_dokumen_feeder", ""), key="edit_link_dokumen_feeder")
            edited_values["keterangan_dokumen"] = st.text_input(
                "Keterangan Dokumen", value=record_data.get("keterangan_dokumen", ""), key="edit_keterangan_dokumen")
            edited_values["link_maps"] = st.text_input(
                "Link Maps", value=record_data.get("link_maps", ""), key="edit_link_maps")

        submitted = st.form_submit_button("Submit Changes")

        if submitted:
            # --- Compare edited_values with original_data ---
            changes_to_update = {}
            for key, new_value in edited_values.items():
                original_value = original_data.get(key)
                # Basic comparison (more robust type handling might be needed)
                # Convert date object from form back to string if original was string or None
                current_new_value = new_value
                if isinstance(new_value, date) and (original_value is None or isinstance(original_value, str)):
                    current_new_value = new_value.strftime('%Y-%m-%d')
                # Handle NaN from number_input
                elif isinstance(new_value, float) and pd.isna(new_value):
                    current_new_value = None

                # Compare (handle None)
                if (original_value is None and current_new_value is not None) or \
                   (original_value is not None and current_new_value is None) or \
                   (original_value is not None and current_new_value is not None and current_new_value != original_value):
                    changes_to_update[key] = current_new_value

            if not changes_to_update:
                st.info("No changes detected.")
                st.session_state.pop('edit_show_confirmation', None)
            else:
                st.warning("The following changes will be applied:")
                st.json(changes_to_update)
                st.session_state.edit_changes_to_confirm = changes_to_update
                st.session_state.edit_identifier = {"fat_id": fat_id_display}
                st.session_state.edit_show_confirmation = True

    # --- Confirmation Section (Outside Form) ---
    if st.session_state.get('edit_show_confirmation'):
        st.subheader("4. Confirm Update")
        st.warning("Are you sure you want to apply these changes?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Update Record", type="primary", key="confirm_update_yes"):
                changes = st.session_state.edit_changes_to_confirm
                identifier = st.session_state.edit_identifier
                id_col, id_val = list(identifier.items())[0]

                with st.spinner("Updating record..."):
                    # Call service update_asset
                    error = asset_data_service.update_asset(
                        identifier_value=id_val,
                        update_data=changes,
                        identifier_col=id_col
                    )

                if error:
                    st.error(f"Update failed: {error}")
                else:
                    st.success("Record updated successfully!")
                    st.balloons()
                    # Clear state after success
                    keys_to_clear = ["edit_search_results", "edit_selected_record_idx", "edit_selected_record_data",
                                     "edit_original_record_data", "edit_show_confirmation", "edit_changes_to_confirm",
                                     "edit_identifier", "edit_columns"]
                    for key in keys_to_clear:
                        st.session_state.pop(key, None)
                    st.rerun()

        with col2:
            if st.button("Cancel Update", key="confirm_update_no"):
                st.session_state.pop('edit_show_confirmation', None)
                st.session_state.pop('edit_changes_to_confirm', None)
                st.session_state.pop('edit_identifier', None)
                st.info("Update cancelled.")
                st.rerun()

# --- Fungsi untuk Bagian Delete ---


def search_for_delete(asset_data_service: AssetDataService):
    """Handles the search UI for the delete process."""
    st.subheader("1. Search Record to Delete")
    col1, col2 = st.columns([1, 3])
    with col1:
        search_option_map = {"FAT ID": "fat_id",
                             "FDT ID": "fdt_id", "OLT Hostname": "hostname_olt"}
        search_display = st.selectbox("Search by", list(
            search_option_map.keys()), key="delete_search_option")
        search_column = search_option_map[search_display]
    with col2:
        search_value = st.text_input("Search value", key="delete_search_value")

    if st.button("Search 🔍", key="delete_search_button"):
        # Clear previous delete state
        keys_to_clear = ["delete_search_results", "delete_selected_record_idx",
                         "delete_record_to_confirm", "delete_show_confirmation"]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

        if not search_value:
            st.warning("Please enter a search value.")
        else:
            with st.spinner("Searching..."):
                df = asset_data_service.search_assets(
                    column_name=search_column, value=search_value)
            if df is not None and not df.empty:
                st.session_state.delete_search_results = df
                st.success(f"Found {len(df)} record(s).")
            elif df is not None:
                st.info("No matching records found.")
            # Error handled by service

    display_search_results("delete_search_results")


def select_and_confirm_delete(asset_data_service: AssetDataService):
    """Handles record selection and delete confirmation UI."""
    if "delete_search_results" not in st.session_state or st.session_state.delete_search_results.empty:
        return

    st.subheader("2. Select Record to Delete")
    df = st.session_state.delete_search_results
    record_options = {
        f"FAT ID: {row['fat_id']} (Index: {idx})": idx for idx, row in df.iterrows()}

    selected_display = st.selectbox("Choose record:", list(record_options.keys()),
                                    key="delete_record_selector", index=None, placeholder="Select a record...")

    if selected_display:
        selected_idx = record_options[selected_display]
        record_to_delete = df.loc[selected_idx].to_dict()
        fat_id_to_delete = record_to_delete.get('fat_id', 'N/A')

        st.subheader("3. Confirm Deletion")
        st.warning(
            f"Are you sure you want to permanently delete this record (FAT ID: {fat_id_to_delete})?")
        st.json(record_to_delete)  # Display record details

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete Record", type="primary", key="confirm_delete_yes"):
                if fat_id_to_delete != 'N/A':
                    with st.spinner("Deleting record..."):
                        # Call service delete_asset
                        error = asset_data_service.delete_asset(
                            identifier_col="fat_id",
                            identifier_value=fat_id_to_delete
                        )

                    if error:
                        st.error(f"Deletion failed: {error}")
                    else:
                        st.success("Record deleted successfully!")
                        st.balloons()
                        # Clear state after success
                        keys_to_clear = ["delete_search_results", "delete_selected_record_idx",
                                         "delete_record_to_confirm", "delete_show_confirmation"]
                        for key in keys_to_clear:
                            st.session_state.pop(key, None)
                        st.rerun()
                else:
                    st.error(
                        "Cannot delete record: Identifier (FAT ID) not found.")

        with col2:
            if st.button("Cancel Deletion", key="confirm_delete_no"):
                st.info("Deletion cancelled.")
                # Rerun to clear selection/confirmation
                st.rerun()

# --- Fungsi App Utama ---


def app(asset_data_service: AssetDataService):
    """
    Main function for the Edit/Delete Asset page, orchestrating the UI flow.

    Args:
        asset_data_service: An instance of AssetDataService.
    """
    st.title("✏️ Edit / ❌ Delete Asset Records")

    if asset_data_service is None:
        st.error("Asset Data Service is not available. Cannot manage records.")
        return

    tab_edit, tab_delete = st.tabs(
        ["Search and Edit ✏️", "Search and Delete ❌"])

    with tab_edit:
        search_for_edit(asset_data_service)
        st.divider()
        select_for_edit(asset_data_service)
        st.divider()
        display_edit_form_and_confirm(asset_data_service)

    with tab_delete:
        search_for_delete(asset_data_service)
        st.divider()
        select_and_confirm_delete(asset_data_service)

# Tidak perlu `if __name__ == "__main__":`

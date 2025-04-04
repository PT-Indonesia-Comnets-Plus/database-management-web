import streamlit as st
import pandas as pd
from utils.database import connect_db
from datetime import date
from copy import deepcopy


def app():
    def fetch_data(db, column_name, value):
        """Fetch records from the 'data_aset' table based on column_name."""
        try:
            cursor = db.cursor()
            query = f'SELECT * FROM data_aset WHERE "{column_name}" = %s'
            cursor.execute(query, (value,))
            records = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return records, columns
        except Exception as e:
            st.error(f"An error occurred while fetching data: {e}")
            return None, None

    def delete_data_record(db, delete_option, delete_value):
        """Delete a record from the 'data_aset' table."""
        # Fetch data to confirm existence
        records, columns = fetch_data(db, delete_option, delete_value)
        if records:
            st.session_state.delete_results = {
                "records": records,
                "columns": columns
            }
        else:
            st.warning("No records found")
            if "delete_results" in st.session_state:
                del st.session_state.delete_results
            return

        # Display results for confirmation
        if "delete_results" in st.session_state:
            st.subheader("Delete Results")
            df = pd.DataFrame(
                st.session_state.delete_results["records"],
                columns=st.session_state.delete_results["columns"]
            )
            st.dataframe(df)

        # Allow user to select a record to delete
        records = st.session_state.delete_results["records"]
        columns = st.session_state.delete_results["columns"]

        st.subheader("Select a Record to Delete")
        selected_delete_idx = st.selectbox(
            "Select record",
            range(len(records)),
            format_func=lambda x: f"Record {x+1} - {records[x][columns.index('FATID')]}",
            key="record_selector"
        )

        if st.button("Confirm Selection", key="confirm_selection"):
            selected_record = records[selected_delete_idx]
            try:
                cursor = db.cursor()
                # Use the selected record's value for deletion
                delete_query = f'DELETE FROM data_aset WHERE "{delete_option}" = %s'
                cursor.execute(
                    delete_query, (selected_record[columns.index(delete_option)],))
                db.commit()
                st.success("✅ Record deleted successfully.")
                # Clear session state after deletion
                del st.session_state.delete_results
            except Exception as e:
                db.rollback()  # Rollback in case of error
                st.error(f"❌ An error occurred while deleting data: {e}")

    def update_data_record(db):
        """Search and display multiple records from the 'data_aset' table."""
        st.subheader("Search Records")

        col1, col2 = st.columns([1, 3])
        with col1:
            search_option = st.selectbox(
                "Search by",
                ["FATID", "FDTID", "OLT"],
                key="search_option"
            )
        with col2:
            search_value = st.text_input(
                "Search value",
                key="search_value",
                on_change=None
            )

        if st.button("Search 🔍", key="search_button"):
            # Clear previous state related to editing
            st.session_state.pop("selected_record", None)
            st.session_state.pop("original_record", None)
            st.session_state.pop("columns", None)
            st.session_state.pop("show_confirmation", None)

            if not search_value:
                st.warning("Please enter a search value")
                return
            else:
                records, columns = fetch_data(db, search_option, search_value)
                if records:
                    st.session_state.search_results = {
                        "records": records,
                        "columns": columns
                    }
                else:
                    st.warning("No records found")
                    st.session_state.pop("search_results", None)

        # Always display the DataFrame if search_results exist
        if "search_results" in st.session_state:
            st.subheader("Search Results")
            df = pd.DataFrame(
                st.session_state.search_results["records"],
                columns=st.session_state.search_results["columns"]
            )
            st.dataframe(df)

    def show_record_selection(db):
        """Show record selection interface after search."""
        if "search_results" not in st.session_state:
            return

        records = st.session_state.search_results["records"]
        columns = st.session_state.search_results["columns"]

        # Allow user to select a record
        st.subheader("Select a Record to Edit")
        selected_idx = st.selectbox(
            "Select record",
            range(len(records)),
            format_func=lambda x: f"Record {x+1} - {records[x][columns.index('FATID')]}",
            key="record_selector"
        )

        if st.button("Confirm Selection", key="confirm_selection"):
            # Ambil FATID atau identifier unik dari record yang dipilih
            selected_fatid = records[selected_idx][columns.index("FATID")]

            # Fetch data ulang dari database
            new_record, new_columns = fetch_data(db, "FATID", selected_fatid)

            if new_record:
                # Update session state dengan data baru
                st.session_state.selected_record = list(
                    new_record[0])  # Data record asli
                st.session_state.original_record = deepcopy(
                    new_record[0])  # Data asli untuk referensi
                st.session_state.columns = new_columns

                # Reset semua input form agar sesuai dengan data baru yang di-fetch
                for col in new_columns:
                    key_name = f"input_{col}"
                    if key_name in st.session_state:
                        # Clear existing form state
                        st.session_state.pop(key_name)

                st.success(
                    "Record reloaded from the database and ready for editing!")
            else:
                st.warning("Failed to reload record from the database.")

    def edit_data(db):
        """Edit the selected record in the 'data_aset' table."""
        if 'selected_record' not in st.session_state:
            st.warning("No record selected for editing.")
            return

        st.subheader("Edit Record Details")
        record = st.session_state.selected_record  # Data yang telah di-fetch ulang
        columns = st.session_state.columns  # Kolom dari database
        original_record = st.session_state.original_record  # Data asli dari database
        new_values = {}

        # Gunakan form untuk input dengan data dari original_record
        with st.form(key="edit_form", clear_on_submit=False):
            # General Information Section
            with st.expander("General Information"):
                new_values["PA"] = st.text_input(
                    "PA",
                    # Gunakan data asli dari record yang di-fetch ulang
                    value=record[columns.index("PA")] or "",
                    key="input_PA"
                )
                # Gunakan nilai yang di-fetch ulang
                tanggal_rfs = record[columns.index("Tanggal RFS")]
                new_values["Tanggal RFS"] = st.date_input(
                    "Tanggal RFS",
                    value=tanggal_rfs or date.today(),
                    key="input_Tanggal_RFS"
                )
                new_values["Mitra"] = st.text_input(
                    "Mitra",
                    # Gunakan data dari record terbaru
                    value=record[columns.index("Mitra")] or "",
                    key="input_Mitra"
                )
                new_values["Kategori"] = st.text_input(
                    "Kategori",
                    # Data terbaru dari database
                    value=record[columns.index("Kategori")] or "",
                    key="input_Kategori"
                )
                new_values["Area KP"] = st.text_input(
                    "Area KP",
                    # Data terbaru dari record
                    value=record[columns.index("Area KP")] or "",
                    key="input_Area_KP"
                )
                new_values["Kota Kab"] = st.text_input(
                    "Kota Kab",
                    # Data terbaru dari database
                    value=record[columns.index("Kota Kab")] or "",
                    key="input_Kota_Kab"
                )

            # OLT Information Section
            with st.expander("OLT Information"):
                new_values["Lokasi OLT"] = st.text_input(
                    "Lokasi OLT", value=record[columns.index("Lokasi OLT")] or "")
                new_values["Hostname OLT"] = st.text_input(
                    "Hostname OLT", value=record[columns.index("Hostname OLT")] or "")
                new_values["Latitude OLT"] = st.text_input(
                    "Latitude OLT", value=record[columns.index("Latitude OLT")] or "")
                new_values["Longtitude OLT"] = st.text_input(
                    "Longtitude OLT", value=record[columns.index("Longtitude OLT")] or "")
                new_values["Brand OLT"] = st.text_input(
                    "Brand OLT", value=record[columns.index("Brand OLT")] or "")
                new_values["Type OLT"] = st.text_input(
                    "Type OLT", value=record[columns.index("Type OLT")] or "")
                new_values["Kapasitas OLT"] = st.number_input(
                    "Kapasitas OLT", min_value=0, value=record[columns.index("Kapasitas OLT")] or 0)
                new_values["Kapasitas port OLT"] = st.number_input(
                    "Kapasitas port OLT", min_value=0, value=record[columns.index("Kapasitas port OLT")] or 0)
                new_values["OLT Port"] = st.number_input(
                    "OLT Port", min_value=0, value=record[columns.index("OLT Port")] or 0)
                new_values["Interface OLT"] = st.text_input(
                    "Interface OLT", value=record[columns.index("Interface OLT")] or "")

            # FDT Information Section
            with st.expander("FDT Information"):
                fdt_new_existing = record[columns.index(
                    "FDT New/Existing")] or "New"
                if fdt_new_existing not in ["New", "Existing"]:
                    fdt_new_existing = "New"
                new_values["FDT New/Existing"] = st.selectbox("FDT New/Existing", [
                    "New", "Existing"], index=["New", "Existing"].index(fdt_new_existing))
                new_values["FDTID"] = st.text_input(
                    "FDT ID", value=record[columns.index("FDTID")] or "")
                new_values["Jumlah Splitter FDT"] = st.number_input(
                    "Jumlah Splitter FDT", min_value=0, value=record[columns.index("Jumlah Splitter FDT")] or 0)
                new_values["Kapasitas Splitter FDT"] = st.number_input(
                    "Kapasitas Splitter FDT", min_value=0, value=record[columns.index("Kapasitas Splitter FDT")] or 0)
                new_values["Latitude FDT"] = st.text_input(
                    "Latitude FDT", value=record[columns.index("Latitude FDT")] or "")
                new_values["Longtitude FDT"] = st.text_input(
                    "Longtitude FDT", value=record[columns.index("Longtitude FDT")] or "")
                new_values["Port FDT"] = st.number_input(
                    "Port FDT", min_value=0, value=record[columns.index("Port FDT")] or 0)
                new_values["Status OSP AMARTA FDT"] = st.text_input(
                    "Status OSP AMARTA FDT", value=record[columns.index("Status OSP AMARTA FDT")] or "")

            # Cluster Information Section
            with st.expander("Cluster Information"):
                new_values["Cluster"] = st.text_input(
                    "Cluster", value=record[columns.index("Cluster")] or "")
                new_values["Latitude Cluster"] = st.text_input(
                    "Latitude Cluster", value=record[columns.index("Latitude Cluster")] or "")
                new_values["Longtitude Cluster"] = st.text_input(
                    "Longtitude Cluster", value=record[columns.index("Longtitude Cluster")] or "")

            # FAT Information Section
            with st.expander("FAT Information"):
                new_values["FATID"] = st.text_input(
                    "FATID", value=record[columns.index("FATID")] or "")
                new_values["Jumlah Splitter FAT"] = st.number_input(
                    "Jumlah Splitter FAT", min_value=0, value=record[columns.index("Jumlah Splitter FAT")] or 0)
                new_values["Kapasitas Splitter FAT"] = st.number_input(
                    "Kapasitas Splitter FAT", min_value=0, value=record[columns.index("Kapasitas Splitter FAT")] or 0)
                new_values["Latitude FAT"] = st.text_input(
                    "Latitude FAT", value=record[columns.index("Latitude FAT")] or "")
                new_values["Longtitude FAT"] = st.text_input(
                    "Longtitude FAT", value=record[columns.index("Longtitude FAT")] or "")
                new_values["Status OSP AMARTA FAT"] = st.text_input(
                    "Status OSP AMARTA FAT", value=record[columns.index("Status OSP AMARTA FAT")] or "")

            # Additional Information Section
            with st.expander("Additional Information"):
                new_values["Kecamatan"] = st.text_input(
                    "Kecamatan", value=record[columns.index("Kecamatan")] or "")
                new_values["Kelurahan"] = st.text_input(
                    "Kelurahan", value=record[columns.index("Kelurahan")] or "")
                new_values["Sumber Datek"] = st.text_input(
                    "Sumber Datek", value=record[columns.index("Sumber Datek")] or "")
                new_values["HC OLD"] = st.number_input(
                    "HC OLD", min_value=0, value=record[columns.index("HC OLD")] or 0)
                new_values["HC iCRM+"] = st.number_input(
                    "HC iCRM+", min_value=0, value=record[columns.index("HC iCRM+")] or 0)
                new_values["TOTAL HC"] = st.number_input(
                    "TOTAL HC", min_value=0, value=record[columns.index("TOTAL HC")] or 0)
                new_values["CLEANSING HP"] = st.text_input(
                    "CLEANSING HP", value=record[columns.index("CLEANSING HP")] or "")
                new_values["OLT"] = st.text_input(
                    "OLT", value=record[columns.index("OLT")] or "")
                new_values["UPDATE ASET"] = st.text_input(
                    "UPDATE ASET", value=record[columns.index("UPDATE ASET")] or "")
                new_values["FAT KONDISI"] = st.text_input(
                    "FAT KONDISI", value=record[columns.index("FAT KONDISI")] or "")
                new_values["FILTER FAT CAP"] = st.text_input(
                    "FILTER FAT CAP", value=record[columns.index("FILTER FAT CAP")] or "")
                new_values["FAT ID X"] = st.text_input(
                    "FAT ID X", value=record[columns.index("FAT ID X")] or "")
                new_values["FAT FILTER PEMAKAIAN"] = st.text_input(
                    "FAT FILTER PEMAKAIAN", value=record[columns.index("FAT FILTER PEMAKAIAN")] or "")
                new_values["KETERANGAN FULL"] = st.text_input(
                    "KETERANGAN FULL", value=record[columns.index("KETERANGAN FULL")] or "")
                new_values["AMARTA UPDATE"] = st.text_input(
                    "AMARTA UPDATE", value=record[columns.index("AMARTA UPDATE")] or "")
                new_values["LINK DOKUMEN FEEDER"] = st.text_input(
                    "LINK DOKUMEN FEEDER", value=record[columns.index("LINK DOKUMEN FEEDER")] or "")
                new_values["KETERANGAN DOKUMEN"] = st.text_input(
                    "KETERANGAN DOKUMEN", value=record[columns.index("KETERANGAN DOKUMEN")] or "")
                new_values["LINK DATA ASET"] = st.text_input(
                    "LINK DATA ASET", value=record[columns.index("LINK DATA ASET")] or "")
                new_values["KETERANGAN DATA ASET"] = st.text_input(
                    "KETERANGAN DATA ASET", value=record[columns.index("KETERANGAN DATA ASET")] or "")
                new_values["LINK MAPS"] = st.text_input(
                    "LINK MAPS", value=record[columns.index("LINK MAPS")] or "")
                new_values["UP3"] = st.text_input(
                    "UP3", value=record[columns.index("UP3")] or "")
                new_values["ULP"] = st.text_input(
                    "ULP", value=record[columns.index("ULP")] or "")

            submitted = st.form_submit_button("Update Record", type="primary")

            if submitted:
                # Pindahkan konfirmasi ke luar form
                st.session_state.show_confirmation = True

        # Bagian konfirmasi di luar form
        if st.session_state.get('show_confirmation', False):
            st.warning("Are you sure you want to update this record?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Update", type="primary"):
                    try:
                        cursor = db.cursor()
                        set_clause = ", ".join(
                            [f'"{col}" = %s' for col in new_values.keys()]
                        )

                        where_conditions = []
                        where_values = []
                        key_columns = ["FATID", "FDTID", "OLT",
                                       "Tanggal RFS", "Hostname OLT"]

                        for col in key_columns:
                            if col in columns:
                                original_value = original_record[columns.index(
                                    col)]
                                if original_value is not None:
                                    where_conditions.append(f'"{col}" = %s')
                                    where_values.append(original_value)

                        if not where_conditions:
                            st.error("No valid conditions for update")
                            return

                        where_clause = " AND ".join(where_conditions)
                        values = list(new_values.values()) + where_values

                        update_query = f"""
                        UPDATE data_aset
                        SET {set_clause}
                        WHERE {where_clause}
                        """

                        cursor.execute(update_query, values)
                        db.commit()

                        if cursor.rowcount == 1:
                            st.success("✅ Record updated successfully!")
                            del st.session_state.selected_record
                            del st.session_state.original_record
                            return
                        else:
                            st.warning(
                                f"⚠️ Unexpected result: {cursor.rowcount} records updated")
                    except Exception as e:
                        st.error(f"An error occurred while updating data: {e}")
            with col2:
                if st.button("Cancel"):
                    del st.session_state.show_confirmation
                    st.rerun()

    # Main App Layout
    st.title("Iconnet Management System 🏥")

    # Initialize database connection
    db = st.session_state.db

    # Create tabs
    tab_home, tab_edit_record, tab_delete_record = st.tabs([
        "Home 🏠",
        "Search and Edit ✏️",
        "Delete Data Record ❌"
    ])

    with tab_home:
        st.subheader("Welcome to Iconnet Management System")
        st.write("Use the tabs above to manage records.")

    with tab_edit_record:
        update_data_record(db)
        show_record_selection(db)
        if 'selected_record' in st.session_state:
            edit_data(db)

    with tab_delete_record:
        st.subheader("Delete a Data Record")
        col1, col2 = st.columns([1, 3])
        with col1:
            delete_option = st.selectbox(
                "Search by",
                ["FATID", "FDTID", "OLT"],
                key="delete_option"
            )
        with col2:
            delete_value = st.text_input(
                "Value to delete",
                key="delete_value",
                on_change=None
            )
        if st.button("search data", key="search_button_delete"):
            if delete_value:
                delete_data_record(db, delete_option, delete_value)
            else:
                st.warning("Please enter a value to delete")

    # Close database connection
    if db and not db.closed:
        db.close()

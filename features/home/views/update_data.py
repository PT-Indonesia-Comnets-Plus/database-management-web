# c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\features\home\views\update_data.py
import streamlit as st
import pandas as pd
from core.services.AssetDataService import AssetDataService  # Import service
from datetime import date, datetime  # Import date and datetime
from copy import deepcopy  # Import deepcopy for manual input check

# Fungsi-fungsi lama (editable_dataframe, insert_data, insert_dataframe, process_uploaded_file)
# telah dihapus karena logikanya dipindahkan ke AssetDataService.


def app(asset_data_service: AssetDataService):
    """
    Provides interfaces for manual asset data input and bulk upload via CSV file,
    utilizing AssetDataService for processing and database interactions.

    Args:
        asset_data_service: An instance of AssetDataService.
    """
    st.title("⬆️ Upload Asset Data")

    if asset_data_service is None:
        st.error("Asset Data Service is not available. Cannot process data.")
        return

    tab_manual, tab_upload = st.tabs(["Manual Input", "Upload File"])

    # --- Tab Input Manual ---
    with tab_manual:
        st.subheader("Manual Data Input")
        st.info(
            "Manual input is complex due to many fields and potential errors. "
            "Using file upload is recommended for multiple entries."
        )

        # Form untuk input manual
        with st.form("manual_input_form", clear_on_submit=True):
            st.write("**Required Fields:**")
            fat_id = st.text_input(
                "FAT ID*", help="Unique identifier for the FAT (e.g., FAT-ABC-001). Mandatory and must be unique.")

            st.divider()
            st.write("**Optional Fields:**")

            # --- Grouping Fields ---
            with st.expander("General Information (Additional Info)"):
                pa = st.text_input("PA", key="manual_pa")
                # Default ke hari ini, bisa diubah pengguna
                tanggal_rfs = st.date_input(
                    "Tanggal RFS", value=None, key="manual_tanggal_rfs", format="YYYY-MM-DD")
                mitra = st.text_input("Mitra", key="manual_mitra")
                kategori = st.text_input("Kategori", key="manual_kategori")
                sumber_datek = st.text_input(
                    "Sumber Datek", key="manual_sumber_datek")

            with st.expander("OLT Information (User Terminals)"):
                hostname_olt = st.text_input(
                    "Hostname OLT", key="manual_hostname_olt")
                latitude_olt = st.number_input("Latitude OLT", value=None, format="%.8f",
                                               key="manual_latitude_olt", help="Decimal format (e.g., -6.12345678)")
                longitude_olt = st.number_input("Longitude OLT", value=None, format="%.8f",
                                                key="manual_longitude_olt", help="Decimal format (e.g., 106.12345678)")
                brand_olt = st.text_input("Brand OLT", key="manual_brand_olt")
                type_olt = st.text_input("Type OLT", key="manual_type_olt")
                kapasitas_olt = st.number_input(
                    "Kapasitas OLT", min_value=0, value=None, step=1, key="manual_kapasitas_olt")
                kapasitas_port_olt = st.number_input(
                    "Kapasitas Port OLT", min_value=0, value=None, step=1, key="manual_kapasitas_port_olt")
                olt_port = st.number_input(
                    "OLT Port", min_value=0, value=None, step=1, key="manual_olt_port")
                olt = st.text_input("OLT", key="manual_olt")
                interface_olt = st.text_input(
                    "Interface OLT", key="manual_interface_olt")

            with st.expander("FDT Information (User Terminals)"):
                fdt_id = st.text_input("FDT ID", key="manual_fdt_id")
                status_osp_amarta_fdt = st.text_input(
                    "Status OSP AMARTA FDT", key="manual_status_osp_amarta_fdt")
                jumlah_splitter_fdt = st.number_input(
                    "Jumlah Splitter FDT", min_value=0, value=None, step=1, key="manual_jumlah_splitter_fdt")
                kapasitas_splitter_fdt = st.number_input(
                    "Kapasitas Splitter FDT", min_value=0, value=None, step=1, key="manual_kapasitas_splitter_fdt")
                fdt_new_existing = st.selectbox(
                    "FDT New/Existing", ["New", "Existing", None], index=2, key="manual_fdt_new_existing")  # Default None
                port_fdt = st.number_input(
                    "Port FDT", min_value=0, value=None, step=1, key="manual_port_fdt")
                latitude_fdt = st.number_input(
                    "Latitude FDT", value=None, format="%.8f", key="manual_latitude_fdt")
                longitude_fdt = st.number_input(
                    "Longitude FDT", value=None, format="%.8f", key="manual_longitude_fdt")

            with st.expander("FAT Information (User Terminals)"):
                # FAT ID sudah di atas
                jumlah_splitter_fat = st.number_input(
                    "Jumlah Splitter FAT", min_value=0, value=None, step=1, key="manual_jumlah_splitter_fat")
                kapasitas_splitter_fat = st.number_input(
                    "Kapasitas Splitter FAT", min_value=0, value=None, step=1, key="manual_kapasitas_splitter_fat")
                latitude_fat = st.number_input(
                    "Latitude FAT", value=None, format="%.8f", key="manual_latitude_fat")
                longitude_fat = st.number_input(
                    "Longitude FAT", value=None, format="%.8f", key="manual_longitude_fat")
                status_osp_amarta_fat = st.text_input(
                    "Status OSP AMARTA FAT", key="manual_status_osp_amarta_fat")
                fat_kondisi = st.text_input(
                    "FAT Kondisi", key="manual_fat_kondisi")
                fat_filter_pemakaian = st.text_input(
                    "FAT Filter Pemakaian", key="manual_fat_filter_pemakaian")
                keterangan_full = st.text_area(
                    "Keterangan Full", key="manual_keterangan_full")
                fat_id_x = st.text_input("FAT ID X", key="manual_fat_id_x")
                filter_fat_cap = st.text_input(
                    "Filter FAT Cap", key="manual_filter_fat_cap")

            with st.expander("Cluster Information (Clusters)"):
                latitude_cluster = st.number_input(
                    "Latitude Cluster", value=None, format="%.8f", key="manual_latitude_cluster")
                longitude_cluster = st.number_input(
                    "Longitude Cluster", value=None, format="%.8f", key="manual_longitude_cluster")
                area_kp = st.text_input("Area KP", key="manual_area_kp")
                kota_kab = st.text_input("Kota/Kab", key="manual_kota_kab")
                kecamatan = st.text_input("Kecamatan", key="manual_kecamatan")
                kelurahan = st.text_input("Kelurahan", key="manual_kelurahan")
                up3 = st.text_input("UP3", key="manual_up3")
                ulp = st.text_input("ULP", key="manual_ulp")

            with st.expander("Home Connected Information (Home Connecteds)"):
                hc_old = st.number_input(
                    "HC OLD", min_value=0, value=None, step=1, key="manual_hc_old")
                hc_icrm = st.number_input(
                    "HC iCRM", min_value=0, value=None, step=1, key="manual_hc_icrm")  # Sesuaikan key jika perlu
                total_hc = st.number_input(
                    "TOTAL HC", min_value=0, value=None, step=1, key="manual_total_hc")
                cleansing_hp = st.text_input(
                    "Cleansing HP", key="manual_cleansing_hp")

            with st.expander("Dokumentasi Information (Dokumentasis)"):
                # status_osp_amarta_fat sudah ada di FAT Info
                link_dokumen_feeder = st.text_input(
                    "Link Dokumen Feeder", key="manual_link_dokumen_feeder")
                keterangan_dokumen = st.text_input(
                    "Keterangan Dokumen", key="manual_keterangan_dokumen")
                link_data_aset = st.text_input(
                    "Link Data Aset", key="manual_link_data_aset")
                keterangan_data_aset = st.text_input(
                    "Keterangan Data Aset", key="manual_keterangan_data_aset")
                link_maps = st.text_input("Link Maps", key="manual_link_maps")
                update_aset = st.text_input(
                    "Update Aset", key="manual_update_aset")
                amarta_update = st.text_input(
                    "AMARTA Update", key="manual_amarta_update")

            # Tombol Submit Form
            submitted = st.form_submit_button("Add Single Asset")

            if submitted:
                if not fat_id:
                    st.warning("FAT ID is required.")
                else:
                    # --- Pre-check for existing FAT ID ---
                    with st.spinner(f"Checking if FAT ID '{fat_id}' already exists..."):
                        existing_df = asset_data_service.search_assets(
                            column_name="fat_id", value=fat_id)

                    if existing_df is not None and not existing_df.empty:
                        st.error(
                            f"FAT ID '{fat_id}' already exists in the database. Cannot insert duplicate.")
                    elif existing_df is None:
                        st.error(
                            "Failed to check for existing FAT ID due to a database error.")
                    else:
                        # --- Kumpulkan data ke dictionary ---
                        # Gunakan nama kolom lowercase sesuai hasil rename pipeline
                        final_data_dict = {
                            "fat_id": fat_id,
                            "pa": pa if pa else None,
                            "tanggal_rfs": tanggal_rfs,  # Objek date atau None
                            "mitra": mitra if mitra else None,
                            "kategori": kategori if kategori else None,
                            "sumber_datek": sumber_datek if sumber_datek else None,
                            "hostname_olt": hostname_olt if hostname_olt else None,
                            "latitude_olt": latitude_olt,
                            "longitude_olt": longitude_olt,
                            "brand_olt": brand_olt if brand_olt else None,
                            "type_olt": type_olt if type_olt else None,
                            "kapasitas_olt": kapasitas_olt,
                            "kapasitas_port_olt": kapasitas_port_olt,
                            "olt_port": olt_port,
                            "olt": olt if olt else None,
                            "interface_olt": interface_olt if interface_olt else None,
                            "fdt_id": fdt_id if fdt_id else None,
                            "status_osp_amarta_fdt": status_osp_amarta_fdt if status_osp_amarta_fdt else None,
                            "jumlah_splitter_fdt": jumlah_splitter_fdt,
                            "kapasitas_splitter_fdt": kapasitas_splitter_fdt,
                            "fdt_new_existing": fdt_new_existing,
                            "port_fdt": port_fdt,
                            "latitude_fdt": latitude_fdt,
                            "longitude_fdt": longitude_fdt,
                            "jumlah_splitter_fat": jumlah_splitter_fat,
                            "kapasitas_splitter_fat": kapasitas_splitter_fat,
                            "latitude_fat": latitude_fat,
                            "longitude_fat": longitude_fat,
                            "status_osp_amarta_fat": status_osp_amarta_fat if status_osp_amarta_fat else None,
                            "fat_kondisi": fat_kondisi if fat_kondisi else None,
                            "fat_filter_pemakaian": fat_filter_pemakaian if fat_filter_pemakaian else None,
                            "keterangan_full": keterangan_full if keterangan_full else None,
                            "fat_id_x": fat_id_x if fat_id_x else None,
                            "filter_fat_cap": filter_fat_cap if filter_fat_cap else None,
                            "latitude_cluster": latitude_cluster,
                            "longitude_cluster": longitude_cluster,
                            "area_kp": area_kp if area_kp else None,
                            "kota_kab": kota_kab if kota_kab else None,
                            "kecamatan": kecamatan if kecamatan else None,
                            "kelurahan": kelurahan if kelurahan else None,
                            "up3": up3 if up3 else None,
                            "ulp": ulp if ulp else None,
                            "hc_old": hc_old,
                            "hc_icrm": hc_icrm,
                            "total_hc": total_hc,
                            "cleansing_hp": cleansing_hp if cleansing_hp else None,
                            "link_dokumen_feeder": link_dokumen_feeder if link_dokumen_feeder else None,
                            "keterangan_dokumen": keterangan_dokumen if keterangan_dokumen else None,
                            "link_data_aset": link_data_aset if link_data_aset else None,
                            "keterangan_data_aset": keterangan_data_aset if keterangan_data_aset else None,
                            "link_maps": link_maps if link_maps else None,
                            "update_aset": update_aset if update_aset else None,
                            "amarta_update": amarta_update if amarta_update else None,
                        }

                        # Buat DataFrame satu baris
                        df_single = pd.DataFrame([final_data_dict])

                        # Konversi tanggal ke string jika perlu sebelum insert
                        if 'tanggal_rfs' in df_single.columns and pd.notna(df_single.loc[0, 'tanggal_rfs']):
                            df_single['tanggal_rfs'] = df_single['tanggal_rfs'].astype(
                                str)

                        st.write("Data to be inserted (Preview):")
                        st.dataframe(df_single)  # Tampilkan DataFrame

                        with st.spinner("Inserting data..."):
                            # Panggil service insert_asset_dataframe dengan DataFrame satu baris
                            processed_count, error_count = asset_data_service.insert_asset_dataframe(
                                df_single)

                        if error_count == 0 and processed_count > 0:
                            st.success(
                                f"Asset data for FAT ID '{fat_id}' inserted successfully!")
                            st.balloons()
                        elif error_count > 0:
                            st.error(
                                f"Failed to insert data for FAT ID '{fat_id}'. Check logs or database constraints.")
                        else:  # processed_count == 0 and error_count == 0
                            st.warning(
                                f"Data for FAT ID '{fat_id}' might already exist or was skipped (e.g., due to ON CONFLICT DO NOTHING).")

    # --- Tab Upload File ---
    with tab_upload:
        st.subheader("Upload Asset File (CSV)")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            key="asset_uploader",
            help="Upload a CSV file with asset data. Ensure columns match the required format."
        )

        if uploaded_file is not None:
            st.write("Processing uploaded file...")
            with st.spinner("Reading and cleaning data from CSV..."):
                # Panggil service process_uploaded_asset_file
                # Hasilnya adalah DataFrame tunggal yang sudah diproses
                processed_df = asset_data_service.process_uploaded_asset_file(
                    uploaded_file)

            if processed_df is not None and not processed_df.empty:  # Tambahkan cek not empty
                st.success("File processed successfully. Preview:")
                st.caption(
                    "You can edit the data below before inserting it into the database.")

                # Gunakan st.data_editor untuk preview dan edit
                edited_df = st.data_editor(
                    processed_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="data_editor_assets",
                    # disabled=["fat_id"] # Opsional: Buat fat_id tidak bisa diedit
                )

                # Simpan DataFrame yang mungkin diedit ke session state
                st.session_state.df_to_upload = edited_df
                st.markdown("---")

                # Tombol untuk memasukkan data ke database
                if st.button("⬆️ Insert Processed Data into Database"):
                    if 'df_to_upload' in st.session_state and not st.session_state.df_to_upload.empty:
                        df_final = st.session_state.df_to_upload
                        st.write(
                            f"Attempting to insert/update {len(df_final)} records...")

                        with st.spinner("Inserting data into database... This might take some time."):
                            # Panggil service insert_asset_dataframe dengan DataFrame tunggal
                            processed_count, error_count = asset_data_service.insert_asset_dataframe(
                                df_final)

                        # Berikan feedback berdasarkan hasil insert dari service
                        if error_count == 0:
                            st.success(
                                f"Successfully processed {processed_count} records from the file.")
                        else:
                            st.warning(
                                f"Attempted to process {len(df_final)} records. "
                                f"Successfully processed: {processed_count}. Failed/Skipped: {error_count}. "
                                "Failures might be due to duplicate FAT IDs (ON CONFLICT DO NOTHING) or other data errors. Check logs for details."
                            )

                        # Hapus state setelah upload
                        del st.session_state.df_to_upload
                        # st.rerun() # Opsional: Rerun untuk membersihkan
                    else:
                        st.warning(
                            "No data available in the editor to upload. Please process a file first.")
            elif processed_df is not None and processed_df.empty:
                st.warning(
                    "The processed file resulted in empty data. Nothing to display or insert.")
            else:
                # Jika process_uploaded_asset_file mengembalikan None
                st.error(
                    "Failed to process the uploaded file. Please check the file format, content, "
                    "and ensure required columns/configurations are correct. Check logs for details."
                )

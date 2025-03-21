import asyncio
import streamlit as st
from utils.database import connect_db
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import os

# Fungsi untuk membuat DataFrame yang dapat diedit


def editable_dataframe(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=True)
    gb.configure_side_bar()
    gb.configure_default_column(editable=True)
    gb.configure_columns(autoSizeColumns='all')

    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,  # Update data saat diubah
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True
    )

    return grid_response["data"]

# Fungsi untuk memasukkan data pasien ke database


async def insert_data(conn, data):
    try:
        query = """
        INSERT INTO patients (PA, Tanggal_RFS, Mitra, Kategori, Area_KP, Kota_Kab, Lokasi_OLT, Hostname_OLT, Latitude_OLT, Longtitude_OLT, Brand_OLT, Type_OLT, Kapasitas_OLT, Kapasitas_port_OLT, OLT_Port, Interface_OLT, FDT_New_Existing, FDT_ID, Jumlah_Splitter_FDT, Kapasitas_Splitter_FDT, Latitude_FDT, Longtitude_FDT, Port_FDT, Status_OSP_AMARTA_FDT, Cluster, Latitude_Cluster, Longtitude_Cluster, FATID, Jumlah Splitter FAT, Kapasitas Splitter FAT, Latitude FAT, Longtitude FAT, Status OSP AMARTA FAT, Kecamatan, Kelurahan, Sumber_Datek, HC_OLD, HC_iCRM, TOTAL_HC, CLEANSING_HP, OLT, UPDATE_ASET, FAT_KONDISI, FILTER_FAT_CAP, FAT_ID_X, FAT_FILTER_PEMAKAIAN, KETERANGAN_FULL, AMARTA_UPDATE, LINK_DOKUMEN_FEEDER, KETERANGAN_DOKUMEN, LINK_DATA_ASET, KETERANGAN_DATA_ASET, LINK_MAPS, UP3, ULP)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, $40, $41, $42, $43, $44, $45, $46, $47, $48, $49, $50, $51, $52, $53, $54, $55)
        """
        await conn.execute(query, *data)
        st.success("Data record inserted successfully.")
    except Exception as e:
        st.error(f"Error inserting patient record: {e}")

# Fungsi untuk mengambil semua data pasien dari database


async def fetch_all_patients(conn):
    try:
        query = "SELECT * FROM datekasetall"
        rows = await conn.fetch(query)
        return rows
    except Exception as e:
        st.error(f"Error fetching patient records: {e}")
        return []

# Fungsi untuk memproses file yang diunggah


def process_uploaded_file(uploaded_file):
    df = pd.read_csv(uploaded_file)

    df.rename(columns={
        "Kordinat OLT": "Koordinat OLT",
        "Koodinat FDT": "Koordinat FDT",
        "Koordinat Cluster": "Koordinat Cluster",
        "Koodinat FAT": "Koordinat FAT"
    }, inplace=True)

    if "Koordinat OLT" in df.columns:
        df[['Latitude OLT', 'Longtitude OLT']
           ] = df['Koordinat OLT'].str.split(',', expand=True)
        df.drop(columns=['Koordinat OLT'], inplace=True)

    if "Koordinat FDT" in df.columns:
        df[['Latitude FDT', 'Longtitude FDT']
           ] = df['Koordinat FDT'].str.split(',', expand=True)
        df.drop(columns=['Koordinat FDT'], inplace=True)

    if "Koordinat Cluster" in df.columns:
        df[['Latitude Cluster', 'Longtitude Cluster']
           ] = df['Koordinat Cluster'].str.split(',', expand=True)
        df.drop(columns=(['Koordinat Cluster']), inplace=True)

    if "Koordinat FAT" in df.columns:
        df[['Latitude FAT', 'Longtitude FAT']
           ] = df['Koordinat FAT'].str.split(',', expand=True)
        df.drop(columns=(['Koordinat FAT']), inplace=True)

    df.fillna({
        "Jumlah Splitter FDT": 0,
        "Kapasitas Splitter FDT": 0,
        "Jumlah Splitter FAT": 0,
        "Kapasitas Splitter FAT": 0,
        "Kapasitas OLT": 0,
        "Kapasitas port OLT": 0,
        "OLT Port": 0,
        "Port FDT": 0,
        "HC OLD": 0,
        "HC iCRM+": 0,
        "TOTAL HC": 0
    }, inplace=True)

    df = df.astype({
        "PA": str,
        "Tanggal RFS": 'datetime64[ns]',
        "Mitra": str,
        "Kategori": str,
        "Area KP": str,
        "Kota Kab": str,
        "Lokasi OLT": str,
        "Hostname OLT": str,
        "Latitude OLT": str,
        "Longtitude OLT": str,
        "Brand OLT": str,
        "Type OLT": str,
        "Kapasitas OLT": int,
        "Kapasitas port OLT": int,
        "OLT Port": int,
        "Interface OLT": str,
        "FDT New/Existing": str,
        "FDTID": str,
        "Jumlah Splitter FDT": int,
        "Kapasitas Splitter FDT": int,
        "Latitude FDT": str,
        "Longtitude FDT": str,
        "Port FDT": int,
        "Status OSP AMARTA FDT": str,
        "Cluster": str,
        "Latitude Cluster": str,
        "Longtitude Cluster": str,
        "FATID": str,
        "Jumlah Splitter FAT": int,
        "Kapasitas Splitter FAT": int,
        "Latitude FAT": str,
        "Longtitude FAT": str,
        "Status OSP AMARTA FAT": str,
        "Kecamatan": str,
        "Kelurahan": str,
        "Sumber Datek": str,
        "HC OLD": int,
        "HC iCRM+": int,
        "TOTAL HC": int,
        "CLEANSING HP": str,
        "OLT": str,
        "UPDATE ASET": str,
        "FAT KONDISI": str,
        "FILTER FAT CAP": str,
        "FAT ID X": str,
        "FAT FILTER PEMAKAIAN": str,
        "KETERANGAN FULL": str,
        "AMARTA UPDATE": str,
        "LINK DOKUMEN FEEDER": str,
        "KETERANGAN DOKUMEN": str,
        "LINK DATA ASET": str,
        "KETERANGAN DATA ASET": str,
        "LINK MAPS": str,
        "UP3": str,
        "ULP": str
    })

    return df


def app():
    if 'db' not in st.session_state:
        st.session_state.db = asyncio.run(connect_db())

    db = st.session_state.db

    st.subheader("Enter details data:")

    if os.path.exists('style.css'):
        with open('style.css') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    input_methods = ["Manual Input", "Upload File"]
    input_method = st.selectbox("Select Input:", input_methods)
    if input_method == "Manual Input":
        with st.form("entry_form", clear_on_submit=True):
            data = []

            with st.expander("General Information"):
                data.append(st.text_input("PA"))
                data.append(st.date_input("Tanggal RFS"))
                data.append(st.text_input("Mitra"))
                data.append(st.text_input("Kategori"))
                data.append(st.text_input("Area KP"))
                data.append(st.text_input("Kota/Kab"))

            with st.expander("OLT Information"):
                data.append(st.text_input("Lokasi OLT"))
                data.append(st.text_input("Hostname OLT"))
                data.append(st.text_input("Latitude OLT"))
                data.append(st.text_input("Longtitude OLT"))
                data.append(st.text_input("Brand OLT"))
                data.append(st.text_input("Type OLT"))
                data.append(st.number_input("Kapasitas OLT", min_value=0))
                data.append(st.number_input(
                    "Kapasitas port OLT", min_value=0))
                data.append(st.text_input("OLT Port"))
                data.append(st.text_input("Interface OLT"))

            with st.expander("FDT Information"):
                data.append(st.selectbox(
                    "FDT New/Existing", ["New", "Existing"]))
                data.append(st.text_input("FDT ID"))
                data.append(st.number_input(
                    "Jumlah Splitter FDT", min_value=0))
                data.append(st.number_input(
                    "Kapasitas Splitter FDT", min_value=0))
                data.append(st.text_input("Latitude FDT"))
                data.append(st.text_input("Longtitude FDT"))
                data.append(st.text_input("Port FDT"))
                data.append(st.text_input("Status OSP AMARTA FDT"))

            with st.expander("Cluster Information"):
                data.append(st.text_input("Cluster"))
                data.append(st.text_input("Latitude Cluster"))
                data.append(st.text_input("Longtitude Cluster"))

            with st.expander("FAT Information"):
                data.append(st.text_input("FATID"))
                data.append(st.number_input(
                    "Jumlah Splitter FAT", min_value=0))
                data.append(st.number_input(
                    "Kapasitas Splitter FAT", min_value=0))
                data.append(st.text_input("Latitude FAT"))
                data.append(st.text_input("Longtitude FAT"))
                data.append(st.text_input("Status OSP AMARTA FAT"))

            with st.expander("Additional Information"):
                data.append(st.text_input("Kecamatan"))
                data.append(st.text_input("Kelurahan"))
                data.append(st.text_input("Sumber Datek"))
                data.append(st.text_input("HC OLD"))
                data.append(st.text_input("HC iCRM+"))
                data.append(st.text_input("TOTAL HC"))
                data.append(st.text_input("CLEANSING HP"))
                data.append(st.text_input("OLT"))
                data.append(st.text_input("UPDATE ASET"))
                data.append(st.text_input("FAT KONDISI"))
                data.append(st.text_input("FILTER FAT CAP"))
                data.append(st.text_input("FAT ID X"))
                data.append(st.text_input("FAT FILTER PEMAKAIAN"))
                data.append(st.text_area("KETERANGAN FULL", height=100))
                data.append(st.text_input("AMARTA UPDATE"))
                data.append(st.text_input("LINK DOKUMEN FEEDER"))
                data.append(st.text_input("KETERANGAN DOKUMEN"))
                data.append(st.text_input("LINK DATA ASET"))
                data.append(st.text_input("KETERANGAN DATA ASET"))
                data.append(st.text_input("LINK MAPS"))
                data.append(st.text_input("UP3"))
                data.append(st.text_input("ULP"))

            submitted = st.form_submit_button("Save Data")
            if submitted:
                asyncio.run(insert_data(db, data))

    elif input_method == "Upload File":

        with st.form("entry_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("Choose a file")

            submitted = st.form_submit_button("Save Data")
            if submitted and uploaded_file is not None:
                df = process_uploaded_file(uploaded_file)
                if df is not None:
                    st.session_state.df_data = df.copy()

        if "df_data" in st.session_state:
            st.write("### **Editable DataFrame**")
            edited_df = editable_dataframe(st.session_state.df_data)
            if st.button("Save Changes"):
                st.session_state.df_data = edited_df
                st.success("Changes Saved!")
            st.write("### **Updated DataFrame**")
            st.dataframe(edited_df)
            if st.button("Upload Data"):
                st.success("Upload Success!")

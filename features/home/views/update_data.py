import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import os


def editable_dataframe(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=True)
    gb.configure_side_bar()
    gb.configure_default_column(editable=True)
    for col in df.columns:
        gb.configure_column(col, auto_size=True)

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


def insert_data(db, data):
    try:
        cursor = db.cursor()

        query = """
        INSERT INTO data_aset ("PA", "Tanggal RFS", "Mitra", "Kategori", "Area KP", "Kota Kab",
            "Lokasi OLT", "Hostname OLT", "Latitude OLT", "Longtitude OLT", "Brand OLT", "Type OLT",
            "Kapasitas OLT", "Kapasitas port OLT", "OLT Port", "Interface OLT", "FDT New/Existing", "FDTID",
            "Jumlah Splitter FDT", "Kapasitas Splitter FDT", "Latitude FDT", "Longtitude FDT", "Port FDT",
            "Status OSP AMARTA FDT", "Cluster", "Latitude Cluster", "Longtitude Cluster", "FATID",
            "Jumlah Splitter FAT", "Kapasitas Splitter FAT", "Latitude FAT", "Longtitude FAT",
            "Status OSP AMARTA FAT", "Kecamatan", "Kelurahan", "Sumber Datek", "HC OLD", "HC iCRM+",
            "TOTAL HC", "CLEANSING HP", "OLT", "UPDATE ASET", "FAT KONDISI", "FILTER FAT CAP",
            "FAT ID X", "FAT FILTER PEMAKAIAN", "KETERANGAN FULL", "AMARTA UPDATE",
            "LINK DOKUMEN FEEDER", "KETERANGAN DOKUMEN", "LINK DATA ASET", "KETERANGAN DATA ASET",
            "LINK MAPS", "UP3", "ULP")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, tuple(data))  # Menggunakan Tuple
        db.commit()
        st.success("Data inserted successfully!")

    except Exception as e:
        db.rollback()  # Rollback transaksi jika terjadi kesalahan
        st.error(f"Error inserting data: {e}")


def insert_dataframe(conn, df):
    try:
        for _, row in df.iterrows():
            data = row.tolist()
            insert_data(conn, data)
    except Exception as e:
        st.error(f"Error inserting data records: {e}")

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

    df['Tanggal RFS'].fillna(pd.Timestamp.now().normalize(), inplace=True)

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
    st.title("Update Data Aset")
    db = st.session_state.db

    if os.path.exists("static\css\style.css"):
        with open("static\css\style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Tabs untuk navigasi
    tab_manual, tab_upload = st.tabs(["Manual Input", "Upload File"])

    # Tab Manual Input
    with tab_manual:
        st.subheader("Manual Data Input")
        with st.form("manual_input_form", clear_on_submit=True):
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
                data.append(st.number_input("Kapasitas port OLT", min_value=0))
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

            submitted = st.form_submit_button("Upload Data")
            if submitted:
                cursor = db.cursor()
                select_query = """SELECT * FROM data_aset WHERE "FATID"=%s"""
                cursor.execute(select_query, (data[28],))
                existing_patient = cursor.fetchone()
                if existing_patient:
                    st.warning("A patient with the same FATID already exists.")
                else:
                    insert_data(db, data)
                    st.success("Data uploaded successfully!")

    # Tab Upload File
    with tab_upload:
        st.subheader("Upload File")
        with st.form("upload_file_form", clear_on_submit=True):  # Berikan key unik untuk form ini
            uploaded_file = st.file_uploader("Choose a file")

            if uploaded_file is not None:
                df = process_uploaded_file(uploaded_file)
                if df is not None:
                    st.session_state.df_data = df.copy()

            if "df_data" in st.session_state:
                st.write("### **Editable DataFrame**")
                # Bisa diedit dalam form
                edited_df = st.data_editor(
                    st.session_state.df_data, num_rows="dynamic")

            if st.form_submit_button("Upload Data"):
                if "df_data" in st.session_state:
                    st.success("Upload Success!")
                else:
                    st.warning("No data to upload")

        if st.button("Insert Data"):
            if "df_data" in st.session_state:
                insert_dataframe(db, st.session_state.df_data)
                st.session_state.pop("df_data")
                st.success("Data inserted successfully!")
            else:
                st.warning("No data to insert")

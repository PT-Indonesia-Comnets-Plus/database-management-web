import streamlit as st
from PIL import Image, ImageOps
from utils.database import connect_db
from utils.cookies import load_cookie_to_session
import os
import pandas as pd
import asyncio

# Load data from cookies
try:
    load_cookie_to_session(st.session_state)
except RuntimeError:
    st.stop()

logo_path = os.path.join("image", "icon.png")
logo = Image.open(logo_path)

logo_resized = logo.resize((40, 50))
padding = 8
new_size = (logo_resized.width + 2 * padding,
            logo_resized.height + 2 * padding)
logo_with_padding = ImageOps.expand(logo_resized, border=padding, fill=(
    255, 255, 255, 0))

try:
    st.set_page_config(page_title="Dashboard Page",
                       page_icon=logo_with_padding)
except st.errors.StreamlitSetPageConfigMustBeFirstCommandError:
    pass


async def load_data():
    conn = await connect_db()
    if conn:
        try:
            # Query ambil data
            rows = await conn.fetch("SELECT * FROM data_aset LIMIT 10")

            # Ambil nama kolom dari hasil query
            colnames = [key for key in rows[0].keys()] if rows else []

            # Masukin data ke Pandas DataFrame
            df = pd.DataFrame(rows, columns=colnames)
            return df
        except Exception as e:
            st.error(f"Query Error: {e}")
            return None
        finally:
            await conn.close()
    else:
        st.warning("Koneksi Database Gagal!")
        return None


async def insert_patient_record(conn, data):
    try:
        query = """
        INSERT INTO patients (PA, Tanggal_RFS, Mitra, Kategori, Area_KP, Kota_Kab, Lokasi_OLT, Hostname_OLT, Latitude_OLT, Longtitude_OLT, Brand_OLT, Type_OLT, Kapasitas_OLT, Kapasitas_port_OLT, OLT_Port, Interface_OLT, FDT_New_Existing, FDT_ID, Jumlah_Splitter_FDT, Kapasitas_Splitter_FDT, Latitude_FDT, Longtitude_FDT, Port_FDT, Status_OSP_AMARTA_FDT, Cluster, Latitude_Cluster, Longtitude_Cluster, FATID, Jumlah_Splitter_FAT, Kapasitas_Splitter_FAT, Latitude_FAT, Longtitude_FAT, Status_OSP_AMARTA_FAT, Kecamatan, Kelurahan, Sumber_Datek, HC_OLD, HC_iCRM, TOTAL_HC, CLEANSING_HP, OLT, UPDATE_ASET, FAT_KONDISI, FILTER_FAT_CAP, FAT_ID_X, FAT_FILTER_PEMAKAIAN, KETERANGAN_FULL, AMARTA_UPDATE, LINK_DOKUMEN_FEEDER, KETERANGAN_DOKUMEN, LINK_DATA_ASET, KETERANGAN_DATA_ASET, LINK_MAPS, UP3, ULP)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, $40, $41, $42, $43, $44, $45, $46, $47, $48, $49, $50, $51, $52, $53, $54, $55)
        """
        await conn.execute(query, *data)
        st.success("Patient record inserted successfully.")
    except Exception as e:
        st.error(f"Error inserting patient record: {e}")


async def fetch_all_patients(conn):
    try:
        query = "SELECT * FROM datekasetall"
        rows = await conn.fetch(query)
        return rows
    except Exception as e:
        st.error(f"Error fetching patient records: {e}")
        return []


def main():
    # Title and sidebar
    st.title("Management System Iconnet:")
    db = st.session_state.db
    df = asyncio.run(load_data())

    menu = ["Home", "Add Data"]
    options = st.sidebar.radio("Select an Option :dart:", menu)
    if options == "Home":
        st.subheader("Welcome to Iconnet Management System")
        st.dataframe(df)

    elif options == "Add Data":
        st.subheader("Enter details data:")
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
                    data.append(st.number_input(
                        "Kapasitas OLT", min_value=0))
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
                    data.append(st.text_area(
                        "KETERANGAN FULL", height=100))
                    data.append(st.text_input("AMARTA UPDATE"))
                    data.append(st.text_input("LINK DOKUMEN FEEDER"))
                    data.append(st.text_input("KETERANGAN DOKUMEN"))
                    data.append(st.text_input("LINK DATA ASET"))
                    data.append(st.text_input("KETERANGAN DATA ASET"))
                    data.append(st.text_input("LINK MAPS"))
                    data.append(st.text_input("UP3"))
                    data.append(st.text_input("ULP"))

                submitted = st.form_submit_button("Save Data")
        elif input_method == "Upload file":
            uploaded_file = st.file_uploader("Choose a file")
            if uploaded_file is not None:
                # Process the uploaded file
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                submitted = st.form_submit_button("Save Data")

    elif options == "Show Records":
        patients = asyncio.run(fetch_all_patients(db))
        if patients:
            st.subheader("All records")
            df = pd.DataFrame(patients, columns=[
                              'PA', 'Tanggal RFS', 'Mitra', 'Kategori', 'Area KP', 'Kota/Kab', 'Lokasi OLT', 'Hostname OLT', 'Latitude OLT', 'Longtitude OLT', 'Brand OLT', 'Type OLT', 'Kapasitas OLT', 'Kapasitas port OLT', 'OLT Port', 'Interface OLT', 'FDT New/Existing', 'FDT ID', 'Jumlah Splitter FDT', 'Kapasitas Splitter FDT', 'Latitude FDT', 'Longtitude FDT', 'Port FDT', 'Status OSP AMARTA FDT', 'Cluster', 'Latitude Cluster', 'Longtitude Cluster', 'FATID', 'Jumlah Splitter FAT', 'Kapasitas Splitter FAT', 'Latitude FAT', 'Longtitude FAT', 'Status OSP AMARTA FAT', 'Kecamatan', 'Kelurahan', 'Sumber Datek', 'HC OLD', 'HC iCRM+', 'TOTAL HC', 'CLEANSING HP', 'OLT', 'UPDATE ASET', 'FAT KONDISI', 'FILTER FAT CAP', 'FAT ID X', 'FAT FILTER PEMAKAIAN', 'KETERANGAN FULL', 'AMARTA UPDATE', 'LINK DOKUMEN FEEDER', 'KETERANGAN DOKUMEN', 'LINK DATA ASET', 'KETERANGAN DATA ASET', 'LINK MAPS', 'UP3', 'ULP'])
            st.dataframe(df)
        else:
            st.write("No data found")

    # Implement other options (Search and Edit Patient, Delete Patients Record, etc.) similarly

    db.close()


if __name__ == "__main__":
    main()

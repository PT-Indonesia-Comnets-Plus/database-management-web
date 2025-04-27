import streamlit as st
import pandas as pd
from core import initialize_session_state


@st.cache_resource
def load_data(_db):
    """Load data aset dari database."""
    conn = _db
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
        SELECT
            -- Kolom dari user_terminals
            ut.fat_id,
            ut.hostname_olt,
            ut.latitude_olt,
            ut.longitude_olt,
            ut.brand_olt,
            ut.type_olt,
            ut.kapasitas_olt,
            ut.kapasitas_port_olt,
            ut.olt_port,
            ut.olt,
            ut.interface_olt,
            ut.fdt_id,
            ut.status_osp_amarta_fdt,
            ut.jumlah_splitter_fdt,
            ut.kapasitas_splitter_fdt,
            ut.fdt_new_existing,
            ut.port_fdt,
            ut.latitude_fdt,
            ut.longitude_fdt,
            ut.jumlah_splitter_fat,
            ut.kapasitas_splitter_fat,
            ut.latitude_fat,
            ut.longitude_fat,
            ut.status_osp_amarta_fat,
            ut.fat_kondisi,
            ut.fat_filter_pemakaian,
            ut.keterangan_full,
            ut.fat_id_x,
            ut.filter_fat_cap,

            -- Kolom dari clusters
            cl.latitude_cluster,
            cl.longitude_cluster,
            cl.area_kp,
            cl.kota_kab,
            cl.kecamatan,
            cl.kelurahan,
            cl.up3,
            cl.ulp,

            -- Kolom dari home_connecteds
            hc.hc_old,
            hc.hc_icrm,
            hc.total_hc,
            hc.cleansing_hp,

            -- Kolom dari dokumentasis (dengan alias untuk status_osp_amarta_fat)
            dk.status_osp_amarta_fat AS dk_status_osp_amarta_fat,
            dk.link_dokumen_feeder,
            dk.keterangan_dokumen,
            dk.link_data_aset,
            dk.keterangan_data_aset,
            dk.link_maps,
            dk.update_aset,
            dk.amarta_update,

            -- Kolom dari additional_informations
            ai.pa,
            ai.tanggal_rfs,
            ai.mitra,
            ai.kategori,
            ai.sumber_datek

        FROM
            user_terminals ut
        LEFT JOIN
            clusters cl ON ut.fat_id = cl.fat_id
        LEFT JOIN
            home_connecteds hc ON ut.fat_id = hc.fat_id
        LEFT JOIN
            dokumentasis dk ON ut.fat_id = dk.fat_id
        LEFT JOIN
            additional_informations ai ON ut.fat_id = ai.fat_id

        -- Batasi hasil query ke 10 baris
        LIMIT 50;
                            """)
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

# features/home/views/dashboard.py
import streamlit as st
import pandas as pd
from core.services.AssetDataService import AssetDataService
import plotly.express as px
import numpy as np
from typing import Optional
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import streamlit.components.v1 as components
from folium.plugins import HeatMap
import geopandas as gpd


@st.cache_data(ttl="1h")
def load_dashboard_data(_service: AssetDataService) -> Optional[pd.DataFrame]:
    """Loads asset data specifically for the dashboard, using caching."""
    print("CACHE MISS: Loading data from database...")
    df = _service.load_all_assets(limit=None)
    return df
# ----------------------------------------------------


def app(asset_data_service: AssetDataService):
    """
    Displays the main dashboard with asset data overview and visualizations.

    Args:
        asset_data_service: An instance of AssetDataService to load data.
    """
    # --- Inject CSS dengan Variabel Warna ---
    st.markdown(r"""
        <style>
            /* --- Definisi Variabel Warna --- */
            :root {
                /* == GANTI WARNA PRIMER DI SINI == */
                --primary-color: #0078d4; /* Contoh: Biru Iconnet/PLN */
                /* =============================== */

                /* Warna turunan (sesuaikan jika perlu) */
                --primary-darker: #005a9e;  /* Lebih gelap untuk teks/aksen */
                --primary-lighter: #f1f7fc; /* Sangat terang untuk background box */
                --primary-light-hover: #e6f2ff; /* Sedikit lebih gelap saat hover box */

                /* Warna Teks Netral */
                --text-dark: #1a1a1a;       /* Untuk nilai KPI */
                --text-medium: #333333;     /* Untuk teks biasa */
                --text-light: #555555;      /* Untuk subtext/keterangan */
                --text-on-primary: #ffffff; /* Teks di atas background primer */

                /* Warna Lain */
                --box-shadow-light: rgba(0, 0, 0, 0.08);
                --box-shadow-hover: rgba(0, 0, 0, 0.15);
                --border-radius-std: 12px;
            }

            /* --- Style Utama --- */
            section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
                max-width: 90%; /* Atau 100% */
            }

            .title {
                font-size: 32px;
                font-weight: bold;
                color: var(--text-on-primary);
                background-color: var(--primary-color); /* Gunakan variabel */
                padding: 15px;
                border-radius: var(--border-radius-std);
                text-align: center;
                box-shadow: 0px 5px 10px var(--box-shadow-light);
                margin-bottom: 25px; /* Sedikit lebih jauh */
            }

            /* --- Style KPI --- */
            .kpi-container, .kpi-hc-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 20px;
                margin-bottom: 25px;
            }
            .kpi-hc-container {
                 grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            }

            .kpi-box {
                background-color: var(--primary-lighter); /* Gunakan variabel */
                padding: 20px;
                border-radius: var(--border-radius-std);
                text-align: center;
                box-shadow: 0 4px 15px var(--box-shadow-light);
                transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease;
            }
            .kpi-box:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px var(--box-shadow-hover);
                background-color: var(--primary-light-hover); /* Warna hover */
                cursor: default;
            }
            .kpi-box h4 {
                font-size: 16px;
                color: var(--primary-darker); /* Gunakan variabel */
                margin-bottom: 10px;
                font-weight: bold;
            }
            .kpi-box p {
                font-size: 24px;
                font-weight: bold;
                color: var(--text-dark); /* Gunakan variabel */
                margin: 0;
            }
            .kpi-hc-container .kpi-box h4 {
                 font-size: 15px;
            }
            .kpi-hc-container .kpi-box p.subtext {
                 font-size: 14px;
                 font-weight: normal;
                 color: var(--text-light); /* Gunakan variabel */
                 margin-top: 5px;
            }

            /* --- Style untuk Expander Insight (jika ada) --- */
            .insight-box {
                background-color: #ffffff; /* Tetap putih atau var(--primary-lighter) */
                border-top: 4px solid var(--primary-color); /* Border atas warna primer */
                padding: 20px;
                border-radius: var(--border-radius-std);
                box-shadow: 0px 10px 20px var(--box-shadow-light);
                font-size: 16px;
                color: var(--text-medium);
                transition: all 0.3s ease;
            }
            .insight-box strong {
                color: var(--primary-darker); /* Aksen warna primer gelap */
            }

        </style>
        """, unsafe_allow_html=True)
    # ------------------------------------------------------

    # --- Judul Utama ---
    st.markdown('<div class="title">DASHBOARD DATA ASET ALL</div>',
                unsafe_allow_html=True)

    # --- Load Data (Tetap sama) ---
    with st.spinner("Loading asset data... (cached if possible)"):
        df_raw = load_dashboard_data(asset_data_service)

    # --- Initial Data Check and Cleaning (Tetap sama) ---
    if df_raw is None:
        st.error("Failed to load asset data from the database.")
        st.stop()
    if df_raw.empty:
        st.info("No asset data found in the database.")
        st.stop()

    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.lower()

    # --- Data Preprocessing & Filtering (Tetap sama) ---
    required_cols = ['kota_kab', 'total_hc', 'brand_olt',
                     'fat_filter_pemakaian', 'fat_id', 'fdt_id', 'olt']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(
            f"Missing required columns in the data: {', '.join(missing_cols)}. Dashboard cannot be fully rendered.")
        st.stop()
    df['total_hc'] = pd.to_numeric(df['total_hc'], errors='coerce')
    invalid_kota = ['local operator', 'none', '']
    df_filtered_global = df[~df['kota_kab'].str.lower().isin(
        invalid_kota)].copy()
    df_filtered_global.dropna(subset=['kota_kab'], inplace=True)
    if df_filtered_global.empty:
        st.warning("No valid data remaining after initial filtering.")
        st.stop()

    # --- Global KPIs (HTML Tetap sama, styling dari CSS) ---
    st.subheader("🔢 Key Performance Indicators (Overall)")
    try:
        total_olt = df_filtered_global['olt'].nunique()
        total_fdt = df_filtered_global['fdt_id'].nunique()
        total_fat = df_filtered_global['fat_id'].nunique()
        total_hc_sum = df_filtered_global['total_hc'].sum()

        kpi_html_1 = f"""
        <div class="kpi-container">
            <div class="kpi-box">
                <h4>🔌 Total Unique OLT</h4>
                <p>{total_olt:,}</p>
            </div>
            <div class="kpi-box">
                <h4>⚡ Total Unique FDT ID</h4>
                <p>{total_fdt:,}</p>
            </div>
            <div class="kpi-box">
                <h4>🧩 Total Unique FAT ID</h4>
                <p>{total_fat:,}</p>
            </div>
            <div class="kpi-box">
                <h4>📊 Total HC</h4>
                <p>{int(total_hc_sum):,} HC</p>
            </div>
        </div>
        """
        st.markdown(kpi_html_1, unsafe_allow_html=True)

        hc_per_kota_global = df_filtered_global.groupby(
            'kota_kab')['total_hc'].sum().reset_index()
        hc_per_kota_global = hc_per_kota_global[hc_per_kota_global['total_hc'] >= 0]

        if not hc_per_kota_global.empty:
            avg_hc_per_kota = hc_per_kota_global['total_hc'].mean()
            max_hc_row = hc_per_kota_global.loc[hc_per_kota_global['total_hc'].idxmax(
            )]
            min_hc_row = hc_per_kota_global.loc[hc_per_kota_global['total_hc'].idxmin(
            )]

            kpi_html_2 = f"""
            <div class="kpi-hc-container">
                <div class="kpi-box">
                    <h4>📊 Avg HC / Kota</h4>
                    <p>{int(avg_hc_per_kota):,} HC</p>
                </div>
                <div class="kpi-box">
                    <h4>🚀 Highest HC</h4>
                    <p>{int(max_hc_row['total_hc']):,} HC</p>
                    <p class="subtext">{max_hc_row['kota_kab']}</p>
                </div>
                <div class="kpi-box">
                    <h4>📉 Lowest HC</h4>
                    <p>{int(min_hc_row['total_hc']):,} HC</p>
                    <p class="subtext">{min_hc_row['kota_kab']}</p>
                </div>
            </div>
            """
            st.markdown(kpi_html_2, unsafe_allow_html=True)
        else:
            st.info("No valid HC data per city found for KPIs.")

    except KeyError as e:
        st.warning(f"Could not calculate KPIs. Missing column: {e}")
    except Exception as e:
        st.error(f"An error occurred during KPI calculation: {e}")

    st.divider()

    # --- Interactive Filtering (Tetap sama) ---
    st.subheader("🔍 Filtered Analysis")
    unique_cities = sorted(df_filtered_global['kota_kab'].unique().tolist())
    invalid_strings_for_select = ['local operator', 'none', '', ' ',  '#n/a']
    unique_cities = [city for city in unique_cities if city.lower(
    ) not in invalid_strings_for_select]
    kota_filter = st.selectbox(
        "Select Kota/Kabupaten for detailed view:",
        ['All'] + unique_cities,
        key="kota_filter_selectbox"
    )
    if kota_filter != 'All':
        df_filtered_selection = df_filtered_global[df_filtered_global['kota_kab'] == kota_filter].copy(
        )
    else:
        # Jika 'All', gunakan data global yang sudah bersih
        df_filtered_selection = df_filtered_global.copy()

    # Cek jika hasil filter (untuk kota spesifik) kosong
    if df_filtered_selection.empty and kota_filter != 'All':
        st.warning(f"No data available for the selected filter: {kota_filter}")

    # --- Visualizations based on Filtered Data ---
    st.subheader(f"Visualizations for: {kota_filter}")
    vis_cols = st.columns(3)

    # Plot 1: Total HC per Kota
    with vis_cols[0]:
        st.markdown("##### Total HC Distribution")
        if kota_filter == 'All':
            total_hc_per_kota = df_filtered_selection.groupby(
                'kota_kab')['total_hc'].sum().reset_index()
            total_hc_per_kota = total_hc_per_kota.sort_values(
                by='total_hc', ascending=False).head(15)
            fig_hc = px.bar(
                total_hc_per_kota, x='kota_kab', y='total_hc', color='kota_kab',
                labels={'total_hc': 'Total HC', 'kota_kab': 'Kota/Kabupaten'}
            )
            fig_hc.update_layout(xaxis_tickangle=-45,
                                 showlegend=False, plot_bgcolor='#F9F8FC')
            st.plotly_chart(fig_hc, use_container_width=True)
        else:
            single_city_hc = df_filtered_selection['total_hc'].sum()
            st.metric(f"Total HC in {kota_filter}",
                      f"{int(single_city_hc):,} HC")

    # Plot 2: OLT Brand Distribution
    with vis_cols[1]:
        st.markdown("##### OLT Brand Distribution")
        if 'brand_olt' in df_filtered_selection.columns:
            brand_olt_counts = df_filtered_selection['brand_olt'].fillna(
                'Unknown').value_counts().reset_index()
            brand_olt_counts.columns = ['brand_olt', 'count']
            if not brand_olt_counts.empty:
                # --- Pertimbangkan warna chart ---
                fig_olt = px.pie(
                    brand_olt_counts, names='brand_olt', values='count', hole=0.3,
                )
                fig_olt.update_traces(
                    textposition='inside', textinfo='percent+label')
                fig_olt.update_layout(plot_bgcolor='white')
                st.plotly_chart(fig_olt, use_container_width=True)
            else:
                st.info("No OLT brand data available for this selection.")
        else:
            st.warning("Column 'brand_olt' not found.")

    # Plot 3: FAT Filter Pemakaian Distribution
    with vis_cols[2]:
        st.markdown("##### FAT Filter Usage")
        if 'fat_filter_pemakaian' in df_filtered_selection.columns:
            fat_filter_counts = df_filtered_selection['fat_filter_pemakaian'].fillna(
                'Unknown').value_counts().reset_index()
            fat_filter_counts.columns = ['fat_filter_pemakaian', 'count']
            if not fat_filter_counts.empty:
                # --- Pertimbangkan warna chart ---
                fig_fat = px.bar(
                    # Default coloring
                    fat_filter_counts, x='fat_filter_pemakaian', y='count', color='fat_filter_pemakaian',
                    title=f"FAT Filter Usage in {kota_filter}",
                    labels={'count': 'Count',
                            'fat_filter_pemakaian': 'FAT Filter Type'}
                )
                fig_fat.update_layout(
                    xaxis_tickangle=-45, showlegend=False, plot_bgcolor='#F9F8FC')
                st.plotly_chart(fig_fat, use_container_width=True)
            else:
                st.info("No FAT filter usage data available for this selection.")
        else:
            st.warning("Column 'fat_filter_pemakaian' not found.")

    # --- Plot 5: Bump Chart (di kolom kedua yang lebih lebar) ---
    vis_cols2 = st.columns([1, 2])

    # Plot 4: Progress Bar HC (di kolom pertama)
    with vis_cols2[0]:
        st.markdown("##### Top 15 HC Distribution (Progress)")
        if kota_filter == 'All':
            # ... (kode progress bar tetap sama) ...
            total_hc_per_kota_prog = df_filtered_selection.groupby(
                'kota_kab')['total_hc'].sum().reset_index()
            total_hc_per_kota_prog.dropna(subset=['total_hc'], inplace=True)
            total_hc_per_kota_prog = total_hc_per_kota_prog.sort_values(
                by='total_hc', ascending=False).head(15)
            if not total_hc_per_kota_prog.empty:
                max_hc_value = total_hc_per_kota_prog['total_hc'].max()
                max_value_for_progress = max(1, max_hc_value)
                st.dataframe(
                    total_hc_per_kota_prog,
                    column_order=("kota_kab", "total_hc"), hide_index=True, width=None, use_container_width=True,
                    column_config={
                        "kota_kab": st.column_config.TextColumn("Kota/Kabupaten"),
                        "total_hc": st.column_config.ProgressColumn(
                            "Total HC", format="%d", min_value=0, max_value=max_value_for_progress
                        )
                    }
                )
            else:
                st.info("No HC data available to display distribution.")
        else:
            st.info("Progress bar view is available when 'All' cities are selected.")

    # --- Plot 5: Bump Chart (di kolom kedua yang lebih lebar) ---
    with vis_cols2[1]:
        # --- PERUBAHAN JUDUL ---
        st.markdown(f"##### Peringkat HC per Tahun (Top 10)")
        # Persiapan data untuk bump chart
        df_bump_chart_base = df_filtered_selection.copy()
        # Pastikan kolom tanggal_rfs ada dan valid
        if 'tanggal_rfs' not in df_bump_chart_base.columns:
            st.warning(
                "Kolom 'tanggal_rfs' tidak ditemukan untuk membuat Bump Chart.")
        else:
            # 1. Pastikan konversi ke datetime
            df_bump_chart_base['tanggal_rfs'] = pd.to_datetime(
                df_bump_chart_base['tanggal_rfs'], errors='coerce')

            # 2. Hapus baris dengan tanggal_rfs NaT ATAU total_hc NaN
            df_bump_chart_base = df_bump_chart_base.dropna(
                subset=['tanggal_rfs', 'total_hc'])

            # 3. Cek jika DataFrame kosong setelah dropna
            if df_bump_chart_base.empty:
                st.info(
                    "Tidak ada data valid ('tanggal_rfs', 'total_hc') untuk Bump Chart.")
            else:
                # 4. Buat kolom Tahun (BUKAN Kuartal)
                try:
                    # --- PERUBAHAN: Ekstrak Tahun ---
                    df_bump_chart_base['Tahun'] = df_bump_chart_base['tanggal_rfs'].dt.year
                    # --- AKHIR PERUBAHAN ---

                    # --- PERUBAHAN: Agregasi per Tahun ---
                    df_agg = df_bump_chart_base.groupby(['Tahun', 'kota_kab'])[
                        'total_hc'].sum().reset_index()
                    # --- AKHIR PERUBAHAN ---

                    # --- PERUBAHAN: Hitung peringkat per Tahun ---
                    df_agg['Rank'] = df_agg.groupby('Tahun')['total_hc'].rank(
                        method='first', ascending=False).astype(int)
                    # --- AKHIR PERUBAHAN ---

                    # Tentukan N kota teratas (logika tetap sama)
                    n_top_cities = 10
                    top_cities_overall = df_agg.groupby(
                        'kota_kab')['total_hc'].sum().nlargest(n_top_cities).index.tolist()

                    # Filter data agregat hanya untuk N kota teratas
                    df_ranked_filtered = df_agg[df_agg['kota_kab'].isin(
                        top_cities_overall)].copy()
                    # --- PERUBAHAN: Urutkan berdasarkan Tahun ---
                    df_ranked_filtered = df_ranked_filtered.sort_values(
                        by=['Tahun', 'Rank'])
                    # --- AKHIR PERUBAHAN ---

                    # --- Buat Bump Chart ---
                    if not df_ranked_filtered.empty:
                        # --- PERUBAHAN: Sumbu X dan Label ---
                        fig_bump = px.line(
                            df_ranked_filtered,
                            x='Tahun',  # Ganti dari 'Kuartal'
                            y='Rank',
                            color='kota_kab',
                            markers=True,
                            text='Rank',
                            # Update label x
                            labels={
                                'Rank': 'Peringkat (1=Tertinggi)', 'kota_kab': 'Kota/Kabupaten', 'Tahun': 'Tahun'}
                        )
                        # --- AKHIR PERUBAHAN ---

                        fig_bump.update_yaxes(autorange="reversed")
                        # --- PERUBAHAN: Hovertemplate ---
                        fig_bump.update_traces(
                            textposition='top center',
                            textfont_size=10,
                            # Ganti Kuartal -> Tahun
                            hovertemplate="<b>%{customdata[0]}</b><br>Tahun: %{x}<br>Peringkat: %{y}<br>Total HC: %{customdata[1]:,}<extra></extra>",
                            customdata=df_ranked_filtered[[
                                'kota_kab', 'total_hc']]
                        )
                        fig_bump.update_layout(
                            plot_bgcolor="#F9F8FC",
                            yaxis_title='Peringkat (1=Tertinggi)',
                            xaxis_title='Tahun',
                            legend_title_text='Kota/Kab'
                        )
                        st.plotly_chart(fig_bump, use_container_width=True)
                    else:
                        st.info(
                            f"Tidak cukup data untuk menampilkan peringkat Top {n_top_cities} kota.")

                except AttributeError as e:
                    st.error(
                        f"Terjadi AttributeError saat membuat kolom Tahun: {e}")
                    st.write("Tipe data kolom 'tanggal_rfs' sebelum error:",
                             df_bump_chart_base['tanggal_rfs'].dtype)
                    st.write("Contoh data 'tanggal_rfs' setelah dropna:",
                             df_bump_chart_base['tanggal_rfs'].head())
                except Exception as e:
                    st.error(
                        f"Terjadi error saat memproses data bump chart: {e}")

    st.divider()
    st.subheader("🗺️ Peta Lokasi Aset")

    # Input pencarian FAT ID
    fat_id_search = st.text_input(
        "Cari FAT ID (kosongkan untuk melihat peta regional/kota):", key="map_fat_id_search").strip()
    df_map_base_selection = df_filtered_selection.copy()
    df_map_base_choropleth = df_filtered_global.copy()

    # Cek kolom penting untuk peta
    required_map_cols_search = ['latitude_fat', 'longitude_fat', 'fat_id',
                                'kota_kab', 'total_hc', 'olt', 'link_dokumen_feeder', 'fat_id_x']
    required_map_cols_choropleth = ['kota_kab', 'fat_id']

    if not all(col in df_map_base_selection.columns for col in required_map_cols_search) or \
       not all(col in df_map_base_choropleth.columns for col in required_map_cols_choropleth):
        st.error(
            f"Kolom peta yang dibutuhkan tidak lengkap. Peta tidak dapat ditampilkan.")
        st.write("Kolom tersedia di df_map_base_selection:",
                 df_map_base_selection.columns.tolist())
        st.write("Kolom tersedia di df_map_base_choropleth:",
                 df_map_base_choropleth.columns.tolist())
        # st.stop() # Hentikan eksekusi jika kolom penting tidak ada
    else:
        # --- Initialize Map ---
        # Center on East Java (default)
        map_center = [-7.5, 112.7]
        map_zoom = 8
        m = folium.Map(location=map_center,
                       zoom_start=map_zoom, tiles="CartoDB positron")

        # --- Conditional Logic: Search vs. Default/City ---
        if fat_id_search:
            # --- Search Mode ---
            st.write(
                f"Mencari FAT ID: **{fat_id_search}** dalam filter '{kota_filter}'")
            # Gunakan df_map_base_selection (data terfilter) untuk search
            df_search_coord = df_map_base_selection.dropna(
                subset=['latitude_fat', 'longitude_fat']).copy()

            if df_search_coord.empty:
                st.warning(
                    f"Tidak ada data lokasi valid untuk mencari '{fat_id_search}' pada filter '{kota_filter}'.")
                search_result = pd.DataFrame()
            else:
                df_search_coord['fat_id_str'] = df_search_coord['fat_id'].astype(
                    str)
                search_result = df_search_coord[df_search_coord['fat_id_str'].str.lower(
                ) == fat_id_search.lower()]

            if not search_result.empty:
                row = search_result.iloc[0]
                # Siapkan popup dan ikon
                hc_value = row['total_hc']
                hc_display = "N/A" if pd.isna(hc_value) else str(int(hc_value))
                link_dokumen = row.get('link_dokumen_feeder', '')
                link_html = f'<a href="{link_dokumen}" target="_blank" style="color: blue;">Klik di sini</a>' if link_dokumen and pd.notna(
                    link_dokumen) else "N/A"
                koordinat_display = f"{row['latitude_fat']:.6f}, {row['longitude_fat']:.6f}"
                fat_id_x = row.get('fat_id_x', None)
                icon_color = 'red' if pd.notna(fat_id_x) and str(
                    fat_id_x).strip().lower() not in ['', 'none'] else 'green'
                icon_shape = 'remove' if icon_color == 'red' else 'ok'
                popup_html = f"""
                 <div style="font-size: 14px; line-height: 1.6; text-align: left; background-color: #f9f9f9; border-radius: 10px; padding: 10px; width: 280px;">
                     <b>Kota/Kab:</b> {row.get('kota_kab', 'N/A')}<br>
                     <b>FAT ID:</b> {row.get('fat_id', 'N/A')}<br>
                     <b>HC:</b> {hc_display}<br>
                     <b>OLT:</b> {row.get('olt', 'N/A')}<br>
                     <b>Koordinat FAT:</b> {koordinat_display}<br>
                     <b>LINK DOKUMEN FEEDER:</b> {link_html}
                 </div>
                 """
                popup = folium.Popup(popup_html, max_width=300)
                # Buat marker dan tambahkan langsung ke peta 'm'
                marker = folium.Marker(
                    location=[row['latitude_fat'], row['longitude_fat']],
                    popup=popup,
                    tooltip=f"FAT ID: {row.get('fat_id', 'N/A')}",
                    icon=folium.Icon(color=icon_color,
                                     icon=icon_shape, prefix='glyphicon')
                )
                marker.add_to(m)
                # Set view peta ke marker
                m.location = [row['latitude_fat'], row['longitude_fat']]
                m.zoom_start = 18
                st.success(f"FAT ID '{fat_id_search}' ditemukan.")
            else:
                st.warning(
                    f"FAT ID '{fat_id_search}' tidak ditemukan dalam data filter '{kota_filter}'.")
                # Biarkan peta default (Choropleth atau marker kota) ditampilkan

        # --- Default Mode (Choropleth atau Marker Kota) ---
        else:  # fat_id_search kosong
            if kota_filter == 'All':
                # --- Choropleth Mode ---
                st.write(
                    f"Menampilkan Peta Agregat FAT per Kota/Kabupaten di Jawa Timur")
                geojson_url = "https://raw.githubusercontent.com/eppofahmi/geojson-indonesia/master/kota/all_kabkota_ind.geojson"
                try:
                    with st.spinner("Memuat data peta regional..."):
                        gdf = gpd.read_file(geojson_url)

                    province_code_column = 'province_id'
                    city_name_column = 'name'
                    east_java_code = '35'

                    if province_code_column not in gdf.columns or city_name_column not in gdf.columns:
                        st.error(
                            "Kolom GeoJSON ('province_id' atau 'name') tidak ditemukan.")
                    else:
                        gdf_jatim = gdf[gdf[province_code_column]
                                        == east_java_code].copy()
                        if gdf_jatim.empty:
                            st.warning(
                                f"Tidak dapat memfilter GeoJSON untuk Jawa Timur (Kode: {east_java_code}).")
                        else:
                            gdf_jatim['name_std_upper'] = gdf_jatim[city_name_column].str.upper(
                            )
                            geojson_std_names_set = set(
                                gdf_jatim['name_std_upper'])

                            def normalize_asset_kota(kota_kab_asset):
                                if pd.isna(kota_kab_asset):
                                    return None
                                kota_kab_upper = str(
                                    kota_kab_asset).strip().upper()
                                if kota_kab_upper in geojson_std_names_set:
                                    return kota_kab_upper
                                elif f"KOTA {kota_kab_upper}" in geojson_std_names_set:
                                    return f"KOTA {kota_kab_upper}"
                                elif f"KABUPATEN {kota_kab_upper}" in geojson_std_names_set:
                                    return f"KABUPATEN {kota_kab_upper}"
                                elif f"KAB. {kota_kab_upper}" in geojson_std_names_set:
                                    return f"KAB. {kota_kab_upper}"
                                else:
                                    return kota_kab_upper

                            df_map_base_choropleth['kota_kab_normalized_join'] = df_map_base_choropleth['kota_kab'].apply(
                                normalize_asset_kota)
                            gdf_jatim_merged = gdf_jatim.merge(
                                df_map_base_choropleth[[
                                    'kota_kab_normalized_join', 'fat_id']],
                                left_on='name_std_upper', right_on='kota_kab_normalized_join', how='left'
                            )
                            fat_counts_final = gdf_jatim_merged.groupby(
                                'name_std_upper')['fat_id'].count().reset_index()
                            fat_counts_final.columns = [
                                'name_std_upper', 'fat_count']

                            # --- Persiapan Tooltip (Tetap sama, fillna(0) penting untuk display) ---
                            count_dict_final = fat_counts_final.set_index('name_std_upper')[
                                'fat_count']
                            gdf_jatim['tooltip_html'] = gdf_jatim.apply(
                                lambda row: f"<b>Kota/Kab:</b> {row[city_name_column]}<br>"
                                            # fillna(0) di sini hanya untuk display di tooltip jika data asli NaN
                                            f"<b>Jumlah FAT:</b> {count_dict_final.fillna(0).astype(int).get(row['name_std_upper'], 0):,}",
                                axis=1
                            )
                            # --- Akhir Persiapan Tooltip ---

                            # --- Buat Choropleth (nan_fill_color sekarang hanya untuk data yg benar2 hilang) ---
                            choropleth = folium.Choropleth(
                                geo_data=gdf_jatim,
                                name='Jumlah FAT per Kota/Kab',
                                data=fat_counts_final,  # Data dengan nilai 0 asli
                                columns=['name_std_upper', 'fat_count'],
                                key_on=f'feature.properties.name_std_upper',
                                fill_color='PuBu',  # Skema warna utama
                                fill_opacity=0.75,
                                line_opacity=0.5,
                                legend_name='Jumlah FAT ID',
                                highlight=True,
                                nan_fill_color='#cccccc',  # Warna abu-abu untuk area TANPA DATA SAMA SEKALI
                                nan_fill_opacity=0.5,  # Opacity untuk area tanpa data
                            ).add_to(m)
                            # --- Akhir Buat Choropleth ---

                            # --- Tambah Tooltip ke Choropleth (Tetap sama) ---
                            tooltip_style_themed = f"""
                                background-color: #F9F8FC;
                                border: 1px solid #d0d0d0;
                                border-radius: 6px;
                                box-shadow: 0px 3px 8px rgba(0, 0, 0, 0.1);
                                padding: 10px 15px;
                                font-size: 13px;
                                font-family: 'Helvetica Neue', Arial, sans-serif;
                                color: #253639;
                                max-width: 250px;
                                white-space: normal;
                            """
                            choropleth.geojson.add_child(
                                folium.features.GeoJsonTooltip(
                                    fields=['tooltip_html'], aliases=[''], label=False, sticky=False, localize=True,
                                    style=tooltip_style_themed
                                )
                            )
                            # --- Akhir Tambah Tooltip ---
                            folium.LayerControl().add_to(m)
                except Exception as e:
                    st.error(f"Gagal memuat/memproses GeoJSON/Choropleth: {e}")
                    st.info("Menampilkan peta dasar Jawa Timur.")

            else:  # kota_filter BUKAN 'All'
                # --- Marker Mode (untuk kota spesifik) ---
                st.write(f"Menampilkan marker FAT untuk: **{kota_filter}**")
                # Gunakan df_map_base_selection (data terfilter) untuk marker kota
                df_map_city = df_map_base_selection.dropna(
                    subset=['latitude_fat', 'longitude_fat']).copy()

                if not df_map_city.empty:
                    # Hitung batas untuk zoom otomatis
                    min_lat, max_lat = df_map_city['latitude_fat'].min(
                    ), df_map_city['latitude_fat'].max()
                    min_lon, max_lon = df_map_city['longitude_fat'].min(
                    ), df_map_city['longitude_fat'].max()
                    # Set peta agar fokus ke batas marker kota ini
                    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

                    # Buat MarkerCluster untuk kota ini
                    marker_cluster_city = MarkerCluster(
                        name=f"FAT di {kota_filter}").add_to(m)

                    # Loop data FAT kota ini dan tambahkan marker ke cluster
                    for idx, row in df_map_city.iterrows():
                        # Siapkan popup (sama seperti di search mode)
                        hc_value = row['total_hc']
                        hc_display = "N/A" if pd.isna(
                            hc_value) else str(int(hc_value))
                        link_dokumen = row.get('link_dokumen_feeder', '')
                        link_html = f'<a href="{link_dokumen}" target="_blank" style="color: blue;">Klik di sini</a>' if link_dokumen and pd.notna(
                            link_dokumen) else "N/A"
                        koordinat_display = f"{row['latitude_fat']:.6f}, {row['longitude_fat']:.6f}"
                        fat_id_x = row.get('fat_id_x', None)
                        icon_color = 'red' if pd.notna(fat_id_x) and str(
                            fat_id_x).strip().lower() not in ['', 'none'] else 'green'
                        icon_shape = 'remove' if icon_color == 'red' else 'ok'
                        popup_html = f"""
                        <div style="font-size: 14px; line-height: 1.6; text-align: left; background-color: #f9f9f9; border-radius: 10px; padding: 10px; width: 280px;">
                            <b>Kota/Kab:</b> {row.get('kota_kab', 'N/A')}<br>
                            <b>FAT ID:</b> {row.get('fat_id', 'N/A')}<br>
                            <b>HC:</b> {hc_display}<br>
                            <b>OLT:</b> {row.get('olt', 'N/A')}<br>
                            <b>Koordinat FAT:</b> {koordinat_display}<br>
                            <b>LINK DOKUMEN FEEDER:</b> {link_html}
                        </div>
                        """
                        popup = folium.Popup(popup_html, max_width=300)

                        # Buat marker dan tambahkan ke CLUSTER
                        marker = folium.Marker(
                            location=[row['latitude_fat'],
                                      row['longitude_fat']],
                            popup=popup,
                            tooltip=f"FAT ID: {row.get('fat_id', 'N/A')}",
                            icon=folium.Icon(
                                color=icon_color, icon=icon_shape, prefix='glyphicon')
                        )
                        # Tambahkan ke cluster kota
                        marker.add_to(marker_cluster_city)

                    # Tambahkan Layer Control
                    folium.LayerControl().add_to(m)

                else:
                    st.warning(
                        f"Tidak ada lokasi FAT yang valid untuk ditampilkan di {kota_filter}.")
                    # Peta 'm' akan ditampilkan, terpusat di Jatim default

        # --- Display Map (di luar semua kondisi if/else) ---
        st.write("Peta Lokasi Aset")

        folium_static(m, width=None, height=600)

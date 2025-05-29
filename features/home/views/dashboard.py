# features/home/views/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from core.services.AssetDataService import AssetDataService
from typing import Optional
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static


@st.cache_data(ttl="1h")
def load_dashboard_data(_service: AssetDataService) -> Optional[pd.DataFrame]:
    """Loads asset data specifically for the dashboard, using caching."""
    print("CACHE MISS: Loading data from database...")
    df = _service.load_all_assets(limit=None)
    return df


@st.cache_data(ttl="2h")
def prepare_map_data(_df: pd.DataFrame, max_markers: int = 1000) -> pd.DataFrame:
    """Prepare and sample map data for better performance."""
    df_map = _df.copy()

    # Clean and validate coordinates
    df_map['latitude_fat'] = pd.to_numeric(
        df_map['latitude_fat'], errors='coerce')
    df_map['longitude_fat'] = pd.to_numeric(
        df_map['longitude_fat'], errors='coerce')
    df_map.dropna(subset=['latitude_fat', 'longitude_fat'], inplace=True)

    # Remove invalid coordinates (outside reasonable bounds for Indonesia)
    df_map = df_map[
        (df_map['latitude_fat'] >= -11) & (df_map['latitude_fat'] <= 6) &
        (df_map['longitude_fat'] >= 95) & (df_map['longitude_fat'] <= 141)
    ]

    # If too many markers, sample the most important ones
    if len(df_map) > max_markers:
        # Prioritize assets with higher HC values
        df_map = df_map.nlargest(max_markers, 'total_hc')
        print(f"Map data sampled to {max_markers} markers for performance")

    return df_map
# ----------------------------------------------------


def _add_markers_to_map_helper(map_object, df_assets, current_filter_context, use_cluster=True):
    """
    Helper function to add asset markers to a Folium map or MarkerCluster.
    Ensures coordinates are valid and creates informative popups.
    Optimized for performance with minimal data processing.
    """
    if df_assets.empty:
        return

    # Limit markers for performance - already handled in prepare_map_data but double-check
    if len(df_assets) > 500:
        df_assets = df_assets.head(500)
        print(
            f"Limited markers to 500 for performance in {current_filter_context}")

    target_map = map_object

    for idx, asset_row in df_assets.iterrows():        # Simplified popup for better performance
        popup_html = f"""
        <div class="custom-marker">
        <div class="marker-title">FAT: {asset_row.get('fat_id', 'N/A')}</div>
        <div class="marker-content">
        <b>Kota:</b> {asset_row.get('kota_kab', 'N/A')}<br>
        <b>HC:</b> {asset_row.get('total_hc', 'N/A')}<br>
        <b>OLT:</b> {asset_row.get('olt', 'N/A')}
        </div>
        </div>
        """

        # Use simpler marker icon for better performance
        folium.CircleMarker(
            location=[asset_row['latitude_fat'], asset_row['longitude_fat']],
            radius=5,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"FAT: {asset_row.get('fat_id', 'N/A')}",
            color='blue',
            fillColor='lightblue',
            fillOpacity=0.7
        ).add_to(target_map)


def app(asset_data_service: AssetDataService):
    """
    Displays the main dashboard with asset data overview and visualizations.

    Args:
        asset_data_service: An instance of AssetDataService to load data.
    """    # CSS styles are now centralized in static/css/style.css
    # ------------------------------------------------------

    # Apply dashboard-specific styling by injecting CSS that targets the current page
    st.markdown("""
    <style>
    /* Dashboard page specific wide layout */
    section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
        max-width: 90% !important;
        margin: 0 auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Judul Utama ---
    st.markdown('<div class="title">DASHBOARD DATA ASET ALL</div>',
                unsafe_allow_html=True)

    # --- Load Data (Tetap sama) ---
    with st.spinner("Loading asset data..."):
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
                <h4>🔌 Total OLT</h4>
                <p>{total_olt:,}</p>
            </div>
            <div class="kpi-box">
                <h4>⚡ Total FDT</h4>
                <p>{total_fdt:,}</p>
            </div>
            <div class="kpi-box">
                <h4>🧩 Total FAT</h4>
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
        if not df_filtered_selection.empty:
            if kota_filter == 'All':
                # For 'All', show HC sum per city
                data_to_plot = df_filtered_selection.groupby(
                    'kota_kab', as_index=False)['total_hc'].sum()
                data_to_plot = data_to_plot.sort_values(
                    by='total_hc', ascending=False)
                if not data_to_plot.empty:
                    fig = px.bar(data_to_plot, x='kota_kab', y='total_hc', title="Total HC per Kota/Kabupaten",
                                 labels={'kota_kab': 'Kota/Kabupaten', 'total_hc': 'Total HC'})
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No HC data to display for {kota_filter}.")
            else:
                # For a specific city, show HC sum per FDT ID within that city
                if 'fdt_id' in df_filtered_selection.columns:
                    data_to_plot = df_filtered_selection.groupby(
                        'fdt_id', as_index=False)['total_hc'].sum()
                    data_to_plot = data_to_plot.sort_values(
                        by='total_hc', ascending=False).head(15)  # Top 15 FDTs
                    if not data_to_plot.empty:
                        fig = px.bar(data_to_plot, x='fdt_id', y='total_hc', title=f"Top HC Distribution by FDT ID in {kota_filter}",
                                     labels={'fdt_id': 'FDT ID', 'total_hc': 'Total HC'})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(
                            f"No HC data by FDT ID to display for {kota_filter}.")
                else:
                    # Fallback: show total HC for the city if FDT ID is not available
                    total_hc_city = df_filtered_selection['total_hc'].sum()
                    st.metric(
                        label=f"Total HC in {kota_filter}", value=f"{int(total_hc_city):,} HC")
                    st.info("FDT ID column not available for detailed breakdown.")
        else:
            st.info(f"No data available for HC Distribution in {kota_filter}.")

    # Plot 2: OLT Brand Distribution
    with vis_cols[1]:
        st.markdown("##### OLT Brand Distribution")
        if 'brand_olt' in df_filtered_selection.columns and not df_filtered_selection.empty:
            brand_counts = df_filtered_selection['brand_olt'].value_counts(
            ).reset_index()
            brand_counts.columns = ['brand_olt', 'count']
            if not brand_counts.empty:
                fig = px.pie(brand_counts, names='brand_olt', values='count', title=f"OLT Brand Distribution in {kota_filter}",
                             hole=0.3)
                fig.update_traces(textposition='inside',
                                  textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No OLT brand data to display for {kota_filter}.")
        else:
            st.info(
                f"OLT Brand data not available or no data for {kota_filter}.")

    # Plot 3: FAT Filter Pemakaian Distribution
    with vis_cols[2]:
        st.markdown("##### FAT Filter Status Distribution")
        if 'fat_filter_pemakaian' in df_filtered_selection.columns and not df_filtered_selection.empty:
            # Clean data: replace None or empty strings
            df_filtered_selection['fat_filter_cleaned'] = df_filtered_selection['fat_filter_pemakaian'].fillna(
                'Unknown').replace('', 'Unknown')
            pemakaian_counts = df_filtered_selection['fat_filter_cleaned'].value_counts(
            ).reset_index()
            pemakaian_counts.columns = ['fat_filter_pemakaian', 'count']
            if not pemakaian_counts.empty:
                fig = px.bar(pemakaian_counts, x='fat_filter_pemakaian', y='count',
                             title=f"Status Pemakaian FAT di {kota_filter}",
                             labels={
                                 'fat_filter_pemakaian': 'Status Pemakaian', 'count': 'Jumlah FAT'},
                             color='fat_filter_pemakaian')
                fig.update_layout(xaxis_title=None,
                                  yaxis_title="Jumlah FAT", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(
                    f"Tidak ada data Status Pemakaian FAT untuk ditampilkan di {kota_filter}.")
        else:
            st.info(
                f"Kolom 'fat_filter_pemakaian' tidak tersedia atau tidak ada data untuk {kota_filter}.")

    # --- Plot 5: Bump Chart (di kolom kedua yang lebih lebar) ---
    vis_cols2 = st.columns([1, 2])

    # Plot 4: Progress Bar HC (di kolom pertama)
    with vis_cols2[0]:
        st.markdown("##### Distribusi HC Teratas")
        if not df_filtered_selection.empty:
            if kota_filter == 'All':
                hc_per_kota_prog = df_filtered_selection.groupby(
                    'kota_kab')['total_hc'].sum().reset_index()
                hc_per_kota_prog = hc_per_kota_prog.sort_values(
                    by='total_hc', ascending=False).head(15)
                if not hc_per_kota_prog.empty:
                    fig = px.bar(hc_per_kota_prog.sort_values(by='total_hc', ascending=True),
                                 x='total_hc', y='kota_kab', orientation='h',
                                 labels={'kota_kab': 'Kota/Kabupaten',
                                         'total_hc': 'Total HC'},
                                 title="Top 15 Kota/Kab by Total HC")
                    fig.update_layout(yaxis_title=None,
                                      xaxis_title="Total HC", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Tidak ada data HC untuk progress bar (Filter: Semua).")
            else:  # Specific city
                hc_by_fat_prog = df_filtered_selection.groupby(
                    'fat_id')['total_hc'].sum().reset_index()
                hc_by_fat_prog = hc_by_fat_prog.sort_values(
                    by='total_hc', ascending=False).head(10)
                if not hc_by_fat_prog.empty:
                    fig = px.bar(hc_by_fat_prog.sort_values(by='total_hc', ascending=True),
                                 x='total_hc', y='fat_id', orientation='h',
                                 labels={'fat_id': 'FAT ID',
                                         'total_hc': 'Total HC'},
                                 title=f"Top 10 FATs by HC di {kota_filter}")
                    fig.update_layout(yaxis_title="FAT ID",
                                      xaxis_title="Total HC", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(
                        f"Tidak ada data HC per FAT untuk progress bar di {kota_filter}.")
        else:
            st.info(
                f"Tidak ada data tersedia untuk visualisasi Distribusi HC Teratas di {kota_filter}.")

    # --- Plot 5: Bump Chart (di kolom kedua yang lebih lebar) ---
    with vis_cols2[1]:
        st.markdown(f"##### Peringkat HC per Tahun (Top 10 Kota/Kab)")
        df_bump_chart_base = df_filtered_selection.copy()
        if 'tanggal_rfs' not in df_bump_chart_base.columns:
            st.warning(
                "Kolom 'tanggal_rfs' tidak ditemukan. Grafik peringkat/tren HC per tahun tidak dapat dibuat.")
        else:
            df_bump_chart_base['tanggal_rfs'] = pd.to_datetime(
                df_bump_chart_base['tanggal_rfs'], errors='coerce')
            df_bump_chart_base.dropna(subset=['tanggal_rfs'], inplace=True)
            df_bump_chart_base['year'] = df_bump_chart_base['tanggal_rfs'].dt.year

            if df_bump_chart_base.empty or 'year' not in df_bump_chart_base.columns or df_bump_chart_base['year'].isnull().all():
                st.info(
                    "Tidak ada data HC dengan informasi tahun yang valid untuk grafik peringkat/tren.")
            else:
                if kota_filter == 'All':
                    yearly_hc = df_bump_chart_base.groupby(['year', 'kota_kab'])[
                        'total_hc'].sum().reset_index()
                    if not yearly_hc.empty:
                        top_cities = yearly_hc.groupby(
                            'kota_kab')['total_hc'].sum().nlargest(10).index
                        yearly_hc_top = yearly_hc[yearly_hc['kota_kab'].isin(
                            top_cities)]
                        if not yearly_hc_top.empty and len(yearly_hc_top['year'].unique()) > 1:
                            yearly_hc_top['rank'] = yearly_hc_top.groupby(
                                'year')['total_hc'].rank(method='dense', ascending=False)
                            fig = px.line(yearly_hc_top, x='year', y='rank', color='kota_kab',
                                          title="Peringkat HC Kota/Kab per Tahun (Top 10)", markers=True,
                                          labels={'rank': 'Peringkat HC (1=Tertinggi)'})
                            fig.update_yaxes(
                                autorange="reversed", tick0=1, dtick=1)
                            st.plotly_chart(fig, use_container_width=True)
                        elif not yearly_hc_top.empty:
                            st.info(
                                "Tidak cukup data tahunan (perlu >1 tahun) untuk membuat grafik peringkat antar kota.")
                        else:
                            st.info(
                                "Tidak cukup data kota untuk membuat grafik peringkat.")
                    else:
                        st.info(
                            "Tidak ada data HC tahunan untuk grafik peringkat (Filter: Semua).")

                else:  # Specific city
                    yearly_hc_city = df_bump_chart_base[df_bump_chart_base['kota_kab'] == kota_filter]
                    yearly_hc_city = yearly_hc_city.groupby(
                        'year')['total_hc'].sum().reset_index()

                    if not yearly_hc_city.empty and len(yearly_hc_city['year'].unique()) > 1:
                        fig = px.line(yearly_hc_city, x='year', y='total_hc',
                                      title=f"Tren Total HC di {kota_filter} per Tahun", markers=True,
                                      labels={'total_hc': 'Total HC', 'year': 'Tahun'})
                        st.plotly_chart(fig, use_container_width=True)
                    elif not yearly_hc_city.empty:
                        st.info(
                            f"Hanya ada data HC untuk satu tahun di {kota_filter}. Grafik tren tidak dapat ditampilkan.")
                    else:
                        st.info(
                            f"Tidak ada data HC tahunan untuk {kota_filter}.")

    st.divider()
    st.subheader("🗺️ Peta Lokasi Aset")

    # Performance toggle
    col_map1, col_map2 = st.columns([3, 1])
    with col_map1:
        fat_id_search = st.text_input(
            "Cari FAT ID (kosongkan untuk melihat peta regional/kota):", key="map_fat_id_search").strip()
    with col_map2:
        show_map = st.checkbox("Tampilkan Peta", value=True,
                               help="Uncheck to skip map loading for faster page load")

    if not show_map:
        st.info("🚀 Peta dinonaktifkan untuk performa yang lebih cepat. Centang kotak 'Tampilkan Peta' untuk melihat peta.")
        return

    # Prepare map data with caching and sampling
    with st.spinner("Mempersiapkan data peta..."):
        df_map_ready = prepare_map_data(
            df_filtered_selection, max_markers=800 if kota_filter == 'All' else 200)

    if df_map_ready.empty:
        st.info(
            f"Tidak ada data aset dengan koordinat valid untuk peta ({kota_filter}).")
        return

    # Cek kolom penting untuk peta
    required_map_cols_search = [
        'latitude_fat', 'longitude_fat', 'fat_id', 'kota_kab', 'total_hc', 'olt']

    if not all(col in df_map_ready.columns for col in required_map_cols_search):
        missing_map_cols = [
            col for col in required_map_cols_search if col not in df_map_ready.columns]
        st.error(
            f"Kolom peta yang dibutuhkan tidak lengkap: {', '.join(missing_map_cols)}.")
        return

    # Initialize map with better performance settings
    map_center_default = [-7.5, 112.7]  # East Java
    map_zoom_default = 8

    # Calculate optimal center based on data
    if not df_map_ready.empty and kota_filter != 'All':
        map_center_default = [
            df_map_ready['latitude_fat'].mean(), df_map_ready['longitude_fat'].mean()]
        map_zoom_default = 10

    with st.spinner("Memuat peta..."):
        m = folium.Map(
            location=map_center_default,
            zoom_start=map_zoom_default,
            tiles="OpenStreetMap",  # Faster than CartoDB
            prefer_canvas=True  # Better performance for many markers
        )

        if fat_id_search:
            # Search functionality
            df_search_result = df_map_ready[
                df_map_ready['fat_id'].astype(str).str.contains(
                    fat_id_search, case=False, na=False)
            ]

            if not df_search_result.empty:
                st.success(
                    f"Ditemukan {len(df_search_result)} aset dengan FAT ID mengandung: '{fat_id_search}'")

                # Center on first result
                first_asset = df_search_result.iloc[0]
                m.location = [first_asset['latitude_fat'],
                              first_asset['longitude_fat']]
                m.zoom_start = 15

                # Add search result markers (no clustering for search results)
                _add_markers_to_map_helper(m, df_search_result.head(
                    50), f"search: {fat_id_search}", use_cluster=False)
            else:
                st.warning(
                    f"FAT ID '{fat_id_search}' tidak ditemukan. Menampilkan peta umum.")
                # Fall back to general view
                marker_cluster = MarkerCluster(
                    name=f"Assets in {kota_filter}",
                    options={'maxClusterRadius': 50,
                             'spiderfyOnMaxZoom': False}
                ).add_to(m)
                _add_markers_to_map_helper(
                    marker_cluster, df_map_ready, kota_filter)
        else:
            # General view with clustering for performance
            if len(df_map_ready) > 100:
                marker_cluster = MarkerCluster(
                    name=f"Assets in {kota_filter}",
                    options={'maxClusterRadius': 50,
                             'spiderfyOnMaxZoom': False}
                ).add_to(m)
                _add_markers_to_map_helper(
                    marker_cluster, df_map_ready, kota_filter)
                st.info(
                    f"Menampilkan {len(df_map_ready)} aset dengan clustering untuk performa optimal.")
            else:
                # Few markers, no need for clustering
                _add_markers_to_map_helper(
                    m, df_map_ready, kota_filter, use_cluster=False)
                # Display map
                st.info(f"Menampilkan {len(df_map_ready)} aset.")
        # Reduced height for better performance
        folium_static(m, width=None, height=500)

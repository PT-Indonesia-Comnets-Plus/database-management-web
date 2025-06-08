# features/home/views/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from core.services.AssetDataService import AssetDataService
from core.utils.database import CACHE_CONFIG
from typing import Optional
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static


# --- Caching and Optimization Functions ---

@st.cache_data(ttl=CACHE_CONFIG['asset_data_ttl'], show_spinner="Loading dashboard data...")
def load_dashboard_data_cached(_service: AssetDataService) -> Optional[pd.DataFrame]:
    """
    Enhanced cached data loading with multiple optimization strategies.
    Uses both Streamlit cache and service-level caching.
    """
    print("CACHE MISS: Loading data from database with enhanced caching...")

    # Use the cached service method
    df = _service.load_all_assets(limit=None)

    if df is not None and not df.empty:
        # Optimize data types for memory efficiency
        df = optimize_dataframe_memory(df)
        print(f"Loaded and optimized {len(df)} records for dashboard")

    return df


@st.cache_data(ttl=CACHE_CONFIG['aggregation_ttl'])
def get_cached_aggregations(_service: AssetDataService, group_by: str) -> Optional[pd.DataFrame]:
    """Get cached aggregated data for visualizations."""
    return _service.get_asset_aggregations(group_by)


@st.cache_data(ttl=CACHE_CONFIG['map_data_ttl'], show_spinner="Preparing map data...")
def prepare_map_data_enhanced(df: pd.DataFrame, max_markers: int = 1000, kota_filter: str = 'All') -> pd.DataFrame:
    """
    Enhanced map data preparation with intelligent caching and optimization.
    """
    print(f"Processing map data for {len(df)} records (filter: {kota_filter})")

    if df.empty:
        return pd.DataFrame()

    df_map = df.copy()

    # Efficient coordinate validation
    numeric_columns = ['latitude_fat', 'longitude_fat']
    for col in numeric_columns:
        if col in df_map.columns:
            df_map[col] = pd.to_numeric(df_map[col], errors='coerce')

    # Remove invalid coordinates
    valid_coords_mask = (
        df_map['latitude_fat'].notna() &
        df_map['longitude_fat'].notna() &
        (df_map['latitude_fat'] >= -11) & (df_map['latitude_fat'] <= 6) &
        (df_map['longitude_fat'] >= 95) & (df_map['longitude_fat'] <= 141)
    )
    # Intelligent sampling based on importance
    df_map = df_map[valid_coords_mask]
    if max_markers is not None and len(df_map) > max_markers:
        # Multi-criteria sampling: HC value + geographical distribution
        if 'total_hc' in df_map.columns:
            # Primary: High HC values
            high_hc = df_map.nlargest(max_markers // 2, 'total_hc')

            # Secondary: Geographical diversity (sample remaining)
            remaining = df_map[~df_map.index.isin(high_hc.index)]
            if not remaining.empty:
                geo_sample = remaining.sample(
                    min(max_markers // 2, len(remaining)))
                df_map = pd.concat([high_hc, geo_sample])
            else:
                df_map = high_hc
        else:
            df_map = df_map.head(max_markers)

        print(f"Map data intelligently sampled to {len(df_map)} markers")
    elif max_markers is None:
        print(f"Map data showing all {len(df_map)} markers (no limit)")

    return df_map


def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame memory usage by converting data types."""
    if df.empty:
        return df

    df_optimized = df.copy()

    # Optimize numeric columns
    for col in df_optimized.select_dtypes(include=['int64']).columns:
        if df_optimized[col].min() >= 0:
            if df_optimized[col].max() < 255:
                df_optimized[col] = df_optimized[col].astype('uint8')
            elif df_optimized[col].max() < 65535:
                df_optimized[col] = df_optimized[col].astype('uint16')
            else:
                df_optimized[col] = df_optimized[col].astype('uint32')
        else:
            if df_optimized[col].min() > -128 and df_optimized[col].max() < 127:
                df_optimized[col] = df_optimized[col].astype('int8')
            elif df_optimized[col].min() > -32768 and df_optimized[col].max() < 32767:
                df_optimized[col] = df_optimized[col].astype('int16')
            else:
                df_optimized[col] = df_optimized[col].astype('int32')

    # Optimize string columns to categories where beneficial
    for col in df_optimized.select_dtypes(include=['object']).columns:
        # Less than 50% unique values
        if df_optimized[col].nunique() / len(df_optimized) < 0.5:
            df_optimized[col] = df_optimized[col].astype('category')

    return df_optimized

# ----------------------------------------------------


def _add_markers_to_map_helper(map_object, df_assets, current_filter_context, use_cluster=True, performance_limit=None):
    """
    Helper function to add asset markers to a Folium map or MarkerCluster.
    Markers use check/cross icons based on fat_id_x field:
    - Green check: fat_id_x is empty/null (good status)
    - Red cross: fat_id_x has value (issue detected)

    Args:
        performance_limit: Maximum number of markers to render (None = unlimited)
    """
    if df_assets.empty:
        return

    # Apply performance limit if specified
    if performance_limit is not None and len(df_assets) > performance_limit:
        df_assets = df_assets.head(performance_limit)
        print(
            f"Limited markers to {performance_limit} for performance in {current_filter_context}")
    elif performance_limit is None:
        print(f"Rendering all {len(df_assets)} markers (no performance limit)")

    target_map = map_object

    for idx, asset_row in df_assets.iterrows():
        lat = asset_row['latitude_fat']
        lon = asset_row['longitude_fat']
        fat_id = asset_row.get('fat_id', 'N/A')
        kota = asset_row.get('kota_kab', 'N/A')
        olt = asset_row.get('olt', 'N/A')
        total_hc = asset_row.get('total_hc', 'N/A')
        link = asset_row.get('link_dokumen_feeder', '#')

        # Check fat_id_x to determine marker icon
        fat_id_x = asset_row.get('fat_id_x', None)
        if pd.isna(fat_id_x) or str(fat_id_x).strip().lower() in ['', 'none', 'nan']:
            icon_color = 'green'
            icon_shape = 'ok'  # checkmark
            status_text = "Status: Normal"
        else:
            icon_color = 'red'
            icon_shape = 'remove'  # cross/X
            status_text = f"Status: Issue - {fat_id_x}"

        # Enhanced popup with check/cross status
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
            <div style="background-color: {'#d4edda' if icon_color == 'green' else '#f8d7da'}; 
                        padding: 8px; border-radius: 5px; margin-bottom: 10px;">
                <h4 style="margin: 0; color: {'#155724' if icon_color == 'green' else '#721c24'};">
                    FAT ID: {fat_id}
                </h4>
            </div>
            <div style="padding: 5px 0;">
                <b>Kota/Kab:</b> {kota}<br>
                <b>OLT:</b> {olt}<br>
                <b>Total HC:</b> {total_hc}<br>
                <b>Link Dokumen:</b> <a href="{link}" target="_blank" style="color: #007bff;">Lihat Dokumen</a><br>
                <b>{status_text}</b>
            </div>
        </div>
        """

        # Use Folium Marker with check/cross icon
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"FAT ID: {fat_id} | {status_text}",
            icon=folium.Icon(color=icon_color,
                             icon=icon_shape, prefix='glyphicon')
        ).add_to(target_map)


def app(asset_data_service: AssetDataService):
    """
    Displays the main dashboard with asset data overview and visualizations.

    Args:
        asset_data_service: An instance of AssetDataService to load data.
    """

    # CSS styles are now centralized in static/css/style.css
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
                unsafe_allow_html=True)    # --- Load Data with Enhanced Caching ---
    df_raw = load_dashboard_data_cached(asset_data_service)

    # --- Initial Data Check and Cleaning (Tetap sama) ---
    if df_raw is None:
        st.error("Failed to load asset data from the database.")
        st.stop()
    if df_raw.empty:
        st.info("No asset data found in the database.")
        st.stop()

    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.lower()

    # --- Data Preprocessing & Filtering (Enhanced) ---
    required_cols = ['kota_kab', 'total_hc', 'brand_olt',
                     'fat_filter_pemakaian', 'fat_id', 'fdt_id', 'olt']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(
            f"Missing required columns in the data: {', '.join(missing_cols)}. Dashboard cannot be fully rendered.")
        st.stop()

    # Clean and normalize data
    df['total_hc'] = pd.to_numeric(df['total_hc'], errors='coerce').fillna(0)

    # Normalize kota_kab names (fix case sensitivity issues like surabaya vs Surabaya)
    df['kota_kab'] = df['kota_kab'].astype(str).str.strip().str.title()

    # Clean fat_filter_pemakaian data (remove anomalies)
    invalid_fat_filter = ['#N/A', '#REF!',
                          'BISA DIPAKAI FAT LOSS', 'NAN', 'NONE', '']
    df['fat_filter_pemakaian'] = df['fat_filter_pemakaian'].astype(
        str).str.upper().str.strip()
    df.loc[df['fat_filter_pemakaian'].isin(
        invalid_fat_filter), 'fat_filter_pemakaian'] = 'UNKNOWN'

    # Clean brand_olt data (normalize and remove anomalies)
    df['brand_olt'] = df['brand_olt'].astype(str).str.strip()
    # Normalize brand names - fix common variations
    brand_mapping = {
        'Fiber Home': 'Fiberhome',
        'FIBER HOME': 'Fiberhome',
        'fiberhome': 'Fiberhome',
        'FIBERHOME': 'Fiberhome',
        'fiber home': 'Fiberhome',
        'ZTE': 'Zte',
        'zte': 'Zte',
        'HUAWEI': 'Huawei',
        'huawei': 'Huawei',
        'BDCOM': 'Bdcom',
        'bdcom': 'Bdcom',
        'RAISECOM': 'Raisecom',
        'raisecom': 'Raisecom',
        '#N/A': 'Unknown',
        '#REF!': 'Unknown',
        'NAN': 'Unknown',
        'NONE': 'Unknown',
        '': 'Unknown',
        'nan': 'Unknown'
    }
    df['brand_olt'] = df['brand_olt'].replace(brand_mapping)

    # Enhanced kota filtering (more comprehensive)
    invalid_kota = ['LOCAL OPERATOR', 'NONE',
                    '', 'NAN', '#N/A', '#REF!', 'UNKNOWN']
    df_filtered_global = df[~df['kota_kab'].str.upper().isin(
        invalid_kota)].copy()
    df_filtered_global.dropna(subset=['kota_kab'], inplace=True)

    # Remove rows with negative HC values (anomalies)
    df_filtered_global = df_filtered_global[df_filtered_global['total_hc'] >= 0]

    if df_filtered_global.empty:
        st.warning("No valid data remaining after enhanced filtering.")
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

        # Enhanced KPI calculations with proper data filtering
        hc_per_kota_global = df_filtered_global.groupby(
            'kota_kab')['total_hc'].sum().reset_index()

        # Remove kota with zero or negative HC values for KPI calculations
        hc_per_kota_global = hc_per_kota_global[hc_per_kota_global['total_hc'] > 0]

        if not hc_per_kota_global.empty:
            # Correct calculation: Average HC per kota (total HC of each kota / number of kotas)
            avg_hc_per_kota = hc_per_kota_global['total_hc'].mean()

            # Highest HC kota
            max_hc_row = hc_per_kota_global.loc[hc_per_kota_global['total_hc'].idxmax(
            )]

            # Lowest HC kota (but still > 0 to avoid anomalies)
            min_hc_row = hc_per_kota_global.loc[hc_per_kota_global['total_hc'].idxmin(
            )]

            kpi_html_2 = f"""
            <div class="kpi-hc-container">
                <div class="kpi-box">
                    <h4>📊 Avg HC / Kota</h4>
                    <p>{int(avg_hc_per_kota):,} HC</p>
                    <p class="subtext">Rata-rata dari {len(hc_per_kota_global)} kota</p>
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

    # --- Interactive Filtering (Enhanced) ---
    st.subheader("🔍 Filtered Analysis")
    unique_cities = sorted(df_filtered_global['kota_kab'].unique().tolist())
    # Enhanced filtering for city selection (remove anomalies)
    invalid_strings_for_select = ['local operator',
                                  'none', '', ' ', '#n/a', 'unknown', 'nan']
    unique_cities = [city for city in unique_cities if city.lower(
    ) not in invalid_strings_for_select]

    kota_filter = st.selectbox(
        "Select Kota/Kabupaten for detailed view:",
        ['All'] + unique_cities,
        key="kota_filter_selectbox"
    )

    # FIXED: Proper filtering logic
    if kota_filter != 'All':
        df_filtered_selection = df_filtered_global[df_filtered_global['kota_kab'] == kota_filter].copy(
        )
    else:
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
            # Enhanced data cleaning for brand OLT
            df_brand_clean = df_filtered_selection.copy()

            # Remove anomalies and normalize values
            invalid_brand_values = ['Unknown',
                                    '#N/A', '#REF!', 'NAN', 'NONE', '']
            df_brand_clean = df_brand_clean[~df_brand_clean['brand_olt'].isin(
                invalid_brand_values)]

            if not df_brand_clean.empty:
                brand_counts = df_brand_clean['brand_olt'].value_counts(
                ).reset_index()
                brand_counts.columns = ['brand_olt', 'count']

                if not brand_counts.empty:
                    fig = px.pie(brand_counts, names='brand_olt', values='count', title=f"OLT Brand Distribution in {kota_filter}",
                                 hole=0.3)
                    fig.update_traces(textposition='inside',
                                      textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(
                        f"No valid OLT brand data to display for {kota_filter}.")
            else:
                st.info(
                    f"No valid OLT brand data after cleaning anomalies for {kota_filter}.")
        else:
            st.info(f"OLT Brand data not available for {kota_filter}.")

    # Plot 3: FAT Filter Pemakaian Distribution
    with vis_cols[2]:
        st.markdown("##### FAT Filter Status Distribution")
        if 'fat_filter_pemakaian' in df_filtered_selection.columns and not df_filtered_selection.empty:
            # Enhanced data cleaning for FAT filter status
            df_filter_clean = df_filtered_selection.copy()

            # Remove anomalies and normalize values
            invalid_filter_values = [
                'UNKNOWN', '#N/A', '#REF!', 'BISA DIPAKAI FAT LOSS', 'NAN', 'NONE', '']
            df_filter_clean = df_filter_clean[~df_filter_clean['fat_filter_pemakaian'].isin(
                invalid_filter_values)]

            if not df_filter_clean.empty:
                pemakaian_counts = df_filter_clean['fat_filter_pemakaian'].value_counts(
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
                        f"No valid FAT filter data to display for {kota_filter}.")
            else:
                st.info(
                    f"No valid FAT filter data after cleaning anomalies for {kota_filter}.")
        else:
            st.info(f"FAT filter data not available for {kota_filter}.")

    # --- Additional Charts ---
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

    # Plot 5: Trend Chart
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
    st.subheader(f"🗺️ Peta Lokasi Aset - {kota_filter}")

    # Show filtering info with debug details
    if kota_filter != 'All':
        unique_cities_in_filtered = df_filtered_selection['kota_kab'].unique(
        ) if not df_filtered_selection.empty else []
        st.info(
            f"📍 Menampilkan peta untuk kota: **{kota_filter}** | Total aset: {len(df_filtered_selection):,}")
        if len(unique_cities_in_filtered) > 1:
            st.warning(
                f"⚠️ Debug: Data masih mengandung {len(unique_cities_in_filtered)} kota: {', '.join(unique_cities_in_filtered[:5])}")
        elif len(unique_cities_in_filtered) == 1:
            st.success(
                f"✅ Data berhasil difilter untuk kota: {unique_cities_in_filtered[0]}")
    else:
        unique_cities_in_filtered = df_filtered_selection['kota_kab'].unique(
        ) if not df_filtered_selection.empty else []
        st.info(
            f"📍 Menampilkan peta untuk semua kota | Total aset: {len(df_filtered_selection):,} | Kota ditemukan: {len(unique_cities_in_filtered)}")

    # Performance toggle
    col_map1, col_map2, col_map3 = st.columns([2, 1, 1])
    with col_map1:
        fat_id_search = st.text_input(
            "Cari FAT ID (kosongkan untuk melihat peta regional/kota):", key="map_fat_id_search").strip()
    with col_map2:
        show_map = st.checkbox("Tampilkan Peta", value=True,
                               help="Uncheck to skip map loading for faster page load")
    with col_map3:
        show_all_data = st.checkbox("Tampilkan Semua Data", value=False,
                                    help="⚠️ PERINGATAN: Menampilkan semua data dapat memperlambat loading")

    if not show_map:
        st.info("🚀 Peta dinonaktifkan untuk performa yang lebih cepat. Centang kotak 'Tampilkan Peta' untuk melihat peta.")
        return

    # Dynamic marker limits based on user choice
    if show_all_data:
        st.warning(
            "⚠️ **Mode Semua Data Aktif**: Rendering mungkin membutuhkan waktu lebih lama untuk dataset besar (>10,000 markers)")
        max_markers_limit = None  # No limit
        performance_limit = None  # No limit in helper function
    else:
        max_markers_limit = 1000 if kota_filter == 'All' else 300
        performance_limit = 500

    # FIXED: Double-check filtering before preparing map data
    if kota_filter != 'All':
        # Ensure data is properly filtered for the selected city
        df_for_map = df_filtered_selection[df_filtered_selection['kota_kab'] == kota_filter].copy(
        )
        if df_for_map.empty:
            st.error(
                f"❌ Tidak ada data untuk kota {kota_filter} setelah filtering ulang.")
            return
        st.success(
            f"✅ Verifikasi filtering: {len(df_for_map)} aset ditemukan untuk {kota_filter}")
    else:
        # Prepare map data with enhanced caching and sampling
        df_for_map = df_filtered_selection.copy()
    with st.spinner("Preparing optimized map data..."):
        df_map_ready = prepare_map_data_enhanced(
            df_for_map,
            max_markers=max_markers_limit,
            kota_filter=kota_filter
        )

    if df_map_ready.empty:
        st.info(
            f"Tidak ada data aset dengan koordinat valid untuk peta ({kota_filter}).")
        return    # Cek kolom penting untuk peta
    required_map_cols_search = [
        'latitude_fat', 'longitude_fat', 'fat_id', 'kota_kab', 'total_hc', 'olt', 'fat_id_x', 'link_dokumen_feeder']

    if not all(col in df_map_ready.columns for col in required_map_cols_search):
        missing_map_cols = [
            col for col in required_map_cols_search if col not in df_map_ready.columns]
        st.error(
            f"Kolom peta yang dibutuhkan tidak lengkap: {', '.join(missing_map_cols)}.")
        return

    # Initialize map with better performance settings
    map_center_default = [-7.5, 112.7]  # East Java
    map_zoom_default = 8

    # Calculate optimal center based on data and selected filter
    if not df_map_ready.empty:
        if kota_filter != 'All':
            # For specific city, center on that city's data
            map_center_default = [
                df_map_ready['latitude_fat'].mean(),
                df_map_ready['longitude_fat'].mean()
            ]
            map_zoom_default = 12  # Zoom closer for specific city        else:
            # For 'All', use broader view but still center on data
            map_center_default = [
                df_map_ready['latitude_fat'].mean(),
                df_map_ready['longitude_fat'].mean()
            ]
            map_zoom_default = 8

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
                    50), f"search: {fat_id_search}", use_cluster=False, performance_limit=50)
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
                    marker_cluster, df_map_ready, kota_filter, performance_limit=performance_limit)
        else:
            # General view with clustering for performance
            if len(df_map_ready) > 100:
                marker_cluster = MarkerCluster(
                    name=f"Assets in {kota_filter}",
                    options={'maxClusterRadius': 50,
                             'spiderfyOnMaxZoom': False}
                ).add_to(m)
                _add_markers_to_map_helper(
                    marker_cluster, df_map_ready, kota_filter, performance_limit=performance_limit)

                # Enhanced success message with city verification
                if kota_filter != 'All':
                    cities_in_map = df_map_ready['kota_kab'].unique(
                    ) if 'kota_kab' in df_map_ready.columns else ['Unknown']
                    if len(cities_in_map) == 1 and cities_in_map[0] == kota_filter:
                        st.success(
                            f"✅ Peta {kota_filter} berhasil dimuat dengan {len(df_map_ready)} aset (dengan clustering)")
                    else:
                        st.warning(
                            f"⚠️ Peta dimuat dengan {len(df_map_ready)} aset, tetapi mengandung kota: {', '.join(cities_in_map[:3])}")
                else:
                    cities_in_map = df_map_ready['kota_kab'].unique(
                    ) if 'kota_kab' in df_map_ready.columns else ['Unknown']
                    st.success(
                        f"✅ Peta semua kota berhasil dimuat dengan {len(df_map_ready)} aset dari {len(cities_in_map)} kota (dengan clustering)")
            else:
                # Few markers, no need for clustering
                _add_markers_to_map_helper(
                    m, df_map_ready, kota_filter, use_cluster=False, performance_limit=performance_limit)

                # Enhanced success message with city verification
                if kota_filter != 'All':
                    cities_in_map = df_map_ready['kota_kab'].unique(
                    ) if 'kota_kab' in df_map_ready.columns else ['Unknown']
                    if len(cities_in_map) == 1 and cities_in_map[0] == kota_filter:
                        st.success(
                            f"✅ Peta {kota_filter} berhasil dimuat dengan {len(df_map_ready)} aset")
                    else:
                        st.warning(
                            f"⚠️ Peta dimuat dengan {len(df_map_ready)} aset, tetapi mengandung kota: {', '.join(cities_in_map[:3])}")
                else:
                    cities_in_map = df_map_ready['kota_kab'].unique(
                    ) if 'kota_kab' in df_map_ready.columns else ['Unknown']
                    st.success(
                        f"✅ Peta semua kota berhasil dimuat dengan {len(df_map_ready)} aset dari {len(cities_in_map)} kota")

        # Reduced height for better performance
        folium_static(m, width=None, height=500)

        # Add marker status summary after the map
        if 'fat_id_x' in df_map_ready.columns:
            normal_count = df_map_ready['fat_id_x'].isna().sum(
            ) + (df_map_ready['fat_id_x'].astype(str).str.strip().str.lower().isin(['', 'none', 'nan'])).sum()
            issue_count = len(df_map_ready) - normal_count

            col1, col2 = st.columns(2)
            with col1:
                st.metric("🟢 FAT Normal", normal_count,
                          help="FAT dengan kondisi masih bisa diisi (fat_id_x kosong)")
            with col2:
                st.metric("🔴 FAT Full", issue_count,
                          help="FAT sudah terisi penuh (fat_id_x terisi)")

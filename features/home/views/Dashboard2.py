import streamlit.components.v1 as components
import plotly.graph_objects as go
from database import load_data  # Pastikan fungsi load_data Anda ada dan berfungsi
import asyncio
# Impor folium_static untuk menampilkan peta
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import folium
import plotly.express as px
import pandas as pd
import streamlit as st
# Set halaman dengan layout yang lebih menarik
st.set_page_config(page_title="Data Dashboard", page_icon="📊", layout="wide")

# Gunakan caching untuk mempercepat pemuatan data


@st.cache_data
def load_data_cached():
    return asyncio.run(load_data())


# Coba load data dengan cache
df = load_data_cached()

# Normalisasi kolom segera setelah load
if df is not None:
    df.columns = df.columns.str.strip()
    if 'Kota/Kab' in df.columns:
        df['Kota/Kab'] = df['Kota/Kab'].astype(str).str.strip().str.title()
        df = df[~df['Kota/Kab'].str.lower().isin(['local operator', 'none', ''])]
        df['Brand OLT'] = df['Brand OLT'].astype(str).str.strip().str.title()
        df['FAT FILTER PEMAKAIAN'] = df['FAT FILTER PEMAKAIAN'].astype(
            str).str.strip().str.title()
        df['Status OSP AMARTA FDT'] = df['Status OSP AMARTA FDT'].astype(
            str).str.strip().str.title()
        df['Kapasitas OLT'] = df['Kapasitas OLT'].astype(str).str.strip()

# CSS kustom
st.markdown("""
    <style>
        .title {
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            background-color: #0078d4;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0px 5px 10px rgba(0,0,0,0.1);
        }
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .kpi-box {
            background-color:#f1f7fc;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .kpi-box:hover {
            transform: translateY(-5px) scale(1.05);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            cursor: pointer;
        }
        .kpi-box h4 {
            font-size: 18px;
            color: #0078d4;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">
    <style>
        .title {
            font-family: 'Open Sans', sans-serif !important;
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            background-color: #00A9B7;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0px 5px 10px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">DASHBOARD DATA ASET ALL</div>',
            unsafe_allow_html=True)

# ✅ Ringkasan Data OLT, FDT, FAT, dan TOTAL HC (versi final)
st.subheader("🔢 Jumlah OLT, FDT, FAT dan Total HC")

# Hitung nilai sesuai logika bisnis
total_olt = df['OLT'].dropna().nunique() if 'OLT' in df.columns else 0
total_fdt = df['FDT ID'].dropna().nunique() if 'FDT ID' in df.columns else 0
total_fat = df['FATID'].count() if 'FATID' in df.columns else 0
total_hc_sum = df['TOTAL HC'].sum() if 'TOTAL HC' in df.columns else 0

# Buat kolom
cols_summary = st.columns(4)

# CSS gaya kotak
st.markdown("""
    <style>
        .summary-box {
            background-color: #f7fafd;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .summary-box:hover {
            transform: translateY(-5px) scale(1.03);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
            cursor: pointer;
        }
    </style>
""", unsafe_allow_html=True)

# Tampilkan box info
with cols_summary[0]:
    st.markdown(f"""
        <div class="summary-box">
            <h4 style="color:#0078d4;">🔌 Total OLT (Unik)</h4>
            <p style="font-size: 24px; font-weight: bold;">{total_olt:,}</p>
        </div>
    """, unsafe_allow_html=True)

with cols_summary[1]:
    st.markdown(f"""
        <div class="summary-box">
            <h4 style="color:#0078d4;">⚡ Total FDT ID (Unik)</h4>
            <p style="font-size: 24px; font-weight: bold;">{total_fdt:,}</p>
        </div>
    """, unsafe_allow_html=True)

with cols_summary[2]:
    st.markdown(f"""
        <div class="summary-box">
            <h4 style="color:#0078d4;">🧩 Total FAT ID</h4>
            <p style="font-size: 24px; font-weight: bold;">{total_fat:,}</p>
        </div>
    """, unsafe_allow_html=True)

with cols_summary[3]:
    st.markdown(f"""
        <div class="summary-box">
            <h4 style="color:#0078d4;">📊 Total HC</h4>
            <p style="font-size: 24px; font-weight: bold;">{int(total_hc_sum):,} HC</p>
        </div>
    """, unsafe_allow_html=True)


# ✅ KPI HC: Rata-rata, Kota Tertinggi, Kota Terendah (tanpa Total HC)
if df is not None and 'Kota/Kab' in df.columns:
    filtered_df = df.copy()

    hc_per_kota = filtered_df.groupby(
        'Kota/Kab')['TOTAL HC'].sum().reset_index()
    hc_per_kota = hc_per_kota[hc_per_kota['TOTAL HC'] >= 0]
    total_hc_sum = hc_per_kota['TOTAL HC'].sum()
    avg_hc_per_kota = hc_per_kota['TOTAL HC'].mean()
    max_hc_row = hc_per_kota.loc[hc_per_kota['TOTAL HC'].idxmax()]
    wilayah_max = max_hc_row['Kota/Kab']
    hc_max = max_hc_row['TOTAL HC']
    min_hc_row = hc_per_kota.loc[hc_per_kota['TOTAL HC'].idxmin()]
    wilayah_min = min_hc_row['Kota/Kab']
    hc_min = min_hc_row['TOTAL HC']

    st.markdown("""
    <style>
        .kpi-container {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 40px;
            margin-top: 30px;
        }
        .kpi-box {
            background-color:#eaf4fc;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            width: 300px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .kpi-box:hover {
            transform: translateY(-5px) scale(1.03);
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            cursor: pointer;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box">
            <h4 style="color:#0078d4; font-size: 18px;">📊 Rata-rata Total HC / Kota</h4>
            <p style="font-size: 28px; font-weight: bold; color: #333;">{int(avg_hc_per_kota):,} HC</p>
        </div>
        <div class="kpi-box">
            <h4 style="color:#0078d4; font-size: 18px;">🚀 Kota/Kab dengan HC Tertinggi</h4>
            <p style="font-size: 20px; color: #0078d4; margin: 4px 0;"><strong>{wilayah_max}</strong></p>
            <p style="font-size: 24px; font-weight: bold; color: #333;">{int(hc_max):,} HC</p>
        </div>
        <div class="kpi-box">
            <h4 style="color:#0078d4; font-size: 18px;">📉 Kota/Kab dengan HC Terendah</h4>
            <p style="font-size: 20px; color: #0078d4; margin: 4px 0;"><strong>{wilayah_min}</strong></p>
            <p style="font-size: 24px; font-weight: bold; color: #333;">{int(hc_min):,} HC</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# Pastikan data ada
if df is not None:

    # Pastikan kolom 'Kota/Kab' ada di dalam DataFrame
    if 'Kota/Kab' in df.columns:
        filtered_df = df  # Menggunakan data penuh tanpa filter

        # Menambahkan filter kota dengan opsi "All"
        kota_filter = st.selectbox(
            "Pilih Kota/Kab", ['All'] + df['Kota/Kab'].unique().tolist())
        # Setelah selectbox kota_filter
        if kota_filter != 'All':
            filtered_df = df[df['Kota/Kab'] == kota_filter]
        else:
            filtered_df = df.copy()

        # ================================
        # 3 Kolom Visualisasi: HC, OLT, FAT
        # ================================

        col1, col2, col3 = st.columns(3)

        # ----- Grafik 1: Total HC per Kota -----
        with col1:
            st.subheader("Total HC per Kota/Kab")
            total_hc_per_kota = filtered_df.groupby(
                'Kota/Kab')['TOTAL HC'].sum().reset_index()
            total_hc_per_kota = total_hc_per_kota.sort_values(
                by='TOTAL HC', ascending=False).head(15)

            fig = px.bar(
                total_hc_per_kota,
                x='Kota/Kab',
                y='TOTAL HC',
                color='Kota/Kab',
                title="Total HC per Kota/Kab",
                labels={'TOTAL HC': 'Total HC', 'Kota/Kab': 'Kota/Kab'}
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=500,
                bargap=0.1,
                showlegend=True,
                plot_bgcolor='white',
                xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray')
            )
            st.plotly_chart(fig, use_container_width=True)

            total_hc_per_kota_full = filtered_df.groupby(
                'Kota/Kab')['TOTAL HC'].sum().reset_index()
            total_hc_sorted = total_hc_per_kota_full.sort_values(
                by='TOTAL HC', ascending=False)
            top_3 = total_hc_sorted.head(3)
            total_hc = total_hc_sorted['TOTAL HC'].sum()
            kontribusi = top_3['TOTAL HC'].sum() / total_hc * 100

        # ----- Grafik 2: Pie Brand OLT -----
        with col2:
            st.subheader("Distribusi Brand OLT")
            brand_olt = filtered_df['Brand OLT'].value_counts().reset_index()
            brand_olt.columns = ['Brand OLT', 'Count']

            brand_olt_fig = px.pie(
                brand_olt,
                names='Brand OLT',
                values='Count',
                title="Distribusi Brand OLT"
            )
            st.plotly_chart(brand_olt_fig, use_container_width=True)
            top_brand = brand_olt.iloc[0]
            total_olt_count = brand_olt['Count'].sum()
            persentase_brand_teratas = (
                top_brand['Count'] / total_olt_count) * 100

        # ----- Grafik 3: FAT per Kota -----
        with col3:
            st.subheader("Distribusi FAT Filter Pemakaian per Kota/Kab")
            fat_filter_per_kota = filtered_df.groupby(
                ['Kota/Kab', 'FAT FILTER PEMAKAIAN']).size().reset_index(name='count')
            top_kota_fat = fat_filter_per_kota.groupby(
                'Kota/Kab')['count'].sum().nlargest(15).index
            fat_filter_per_kota = fat_filter_per_kota[fat_filter_per_kota['Kota/Kab'].isin(
                top_kota_fat)]

            fat_filter_fig = px.bar(
                fat_filter_per_kota,
                x='Kota/Kab',
                y='count',
                color='FAT FILTER PEMAKAIAN',
                labels={'count': 'Jumlah', 'Kota/Kab': 'Kota/Kab'}
            )
            fat_filter_fig.update_layout(
                barmode='stack', xaxis_tickangle=-45, height=450)
            st.plotly_chart(fat_filter_fig, use_container_width=True)

        # ================================
        # Kotak Insight 3 Buah di 1 Baris
        # ================================
        # ===== CSS BOX MODERN =====
    # ================================
# Kotak Insight 3 Buah di 1 Baris
# ================================
# ===== CSS BOX MODERN =====
# --- INSIGHT GLOBAL (TIDAK IKUT FILTER KOTA) ---

# Insight Total HC
hc_global = df.groupby('Kota/Kab')['TOTAL HC'].sum().reset_index()
hc_global = hc_global.sort_values(by='TOTAL HC', ascending=False)
top_3 = hc_global.head(3)
total_hc_global = hc_global['TOTAL HC'].sum()
kontribusi = top_3['TOTAL HC'].sum() / total_hc_global * \
    100 if total_hc_global > 0 else 0

# Insight Brand OLT
brand_olt_global = df['Brand OLT'].value_counts().reset_index()
brand_olt_global.columns = ['Brand OLT', 'Count']
top_brand = brand_olt_global.iloc[0] if not brand_olt_global.empty else {
    'Brand OLT': '-', 'Count': 0}
total_olt_global = brand_olt_global['Count'].sum()
persentase_brand_teratas = (
    top_brand['Count'] / total_olt_global * 100) if total_olt_global > 0 else 0

# Insight FAT Filter
fat_global = df.groupby(['Kota/Kab', 'FAT FILTER PEMAKAIAN']
                        ).size().reset_index(name='count')
fat_dom = fat_global.groupby('FAT FILTER PEMAKAIAN')[
    'count'].sum().reset_index()
fat_dom = fat_dom.sort_values(by='count', ascending=False)
top_fat = fat_dom.iloc[0] if not fat_dom.empty else {
    'FAT FILTER PEMAKAIAN': '-', 'count': 0}
total_fat_all = fat_dom['count'].sum()
fat_persen = (top_fat['count'] / total_fat_all *
              100) if total_fat_all > 0 else 0

st.markdown("""
    <style>
        .insight-box {
            background-color: #ffffff;
            border-top: 4px solid #0078d4;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0px 10px 20px rgba(0, 0, 0, 0.08);
            font-size: 16px;
            color: #333;
            transition: all 0.3s ease;
        }
        .insight-box strong {
            color: #0078d4;
        }
        .insight-box span.icon {
            font-size: 22px;
            margin-right: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# ===== 3 KOLOM EXPANDER =====
with st.container():
    insight1, insight2, insight3 = st.columns(3)

    with insight1:
        with st.expander("📌 Insight Total HC per Kota"):
            st.markdown(f"""
                <div class="insight-box">
                    Kota dengan HC terbesar adalah <strong>{top_3.iloc[0]['Kota/Kab']}</strong> 
                    dengan <strong>{int(top_3.iloc[0]['TOTAL HC']):,} HC</strong>, diikuti oleh 
                    <strong>{top_3.iloc[1]['Kota/Kab']}</strong> dan <strong>{top_3.iloc[2]['Kota/Kab']}</strong>. 
                    Ketiga kota ini menyumbang sekitar <strong>{kontribusi:.1f}%</strong> dari total HC.
                </div>
            """, unsafe_allow_html=True)

    with insight2:
        with st.expander("📌 Insight Brand OLT"):
            st.markdown(f"""
                <div class="insight-box">
                    Brand OLT paling banyak adalah <strong>{top_brand['Brand OLT']}</strong> 
                    dengan <strong>{top_brand['Count']:,} unit</strong>, mencakup sekitar 
                    <strong>{persentase_brand_teratas:.1f}%</strong> dari total perangkat OLT.
                </div>
            """, unsafe_allow_html=True)

    with insight3:
        with st.expander("📌 Insight FAT Filter Pemakaian"):
            if not fat_dom.empty:
                st.markdown(f"""
                    <div class="insight-box">
                        FAT Filter Pemakaian terbanyak adalah <strong>{top_fat['FAT FILTER PEMAKAIAN']}</strong> 
                        dengan <strong>{top_fat['count']:,} titik</strong>, mencakup sekitar 
                        <strong>{fat_persen:.1f}%</strong> dari total penggunaan FAT.
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Tidak ada data FAT Filter yang bisa dianalisis.")

# ================================
# Ranking 5 Kota/Kab dengan Total HC Terbanyak
# ================================

# Hitung ulang Total HC per Kota dari filtered_df
total_hc_per_kota = filtered_df.groupby(
    'Kota/Kab')['TOTAL HC'].sum().reset_index()
top_5_clusters = total_hc_per_kota.sort_values(
    by='TOTAL HC', ascending=False).head(5).reset_index(drop=True)
top_5_clusters['Ranking'] = top_5_clusters.index + 1
top_5_clusters['Label'] = top_5_clusters['Ranking'].astype(
    str) + ". " + top_5_clusters['Kota/Kab']

# Judul grafik
st.markdown("## 🏆 Ranking 5 Kota/Kab dengan Total HC Terbanyak")

# Grafik horizontal bar dengan gradasi warna berdasarkan Ranking
fig = px.bar(
    top_5_clusters.sort_values('Ranking'),
    x='TOTAL HC',
    y='Label',
    orientation='h',
    text='TOTAL HC',
    color='Ranking',  # pakai gradasi berdasarkan ranking
    color_continuous_scale='Viridis',  # bisa diganti: 'Teal', 'Viridis', dst.
    labels={'Label': 'Kota/Kab', 'TOTAL HC': 'Total HC'}
)

# Update tampilan grafik
fig.update_traces(
    texttemplate='%{text:,} HC',
    textposition='outside',
    hovertemplate='<b>%{y}</b><br>Total HC: %{x:,} HC<extra></extra>'
)

fig.update_coloraxes(showscale=False)  # sembunyikan legenda skala warna

fig.update_layout(
    height=400,
    yaxis=dict(autorange='reversed'),
    showlegend=False,
    plot_bgcolor='white',
    margin=dict(t=40, l=80, r=30, b=40)
)

# Tampilkan grafik
st.plotly_chart(fig, use_container_width=True)

# ================================
# Tabel Data Detail
# ================================
# CSS: Tag multiselect warna biru Iconnet PLN
# =============================
# 💠 CSS: Bikin Tag Multiselect Warna Biru Iconnet PLN
# =============================
st.markdown("""
    <style>
    /* Override warna chip/tag di multiselect secara paksa */
    [data-baseweb="tag"] {
        background-color: #00A9E0 !important;
        color: #ffffff !important;
        font-weight: bold;
        border: none !important;
    }

    /* Override warna ikon close (X) */
    [data-baseweb="tag"] svg {
        fill: white !important;
    }

    /* Kalau masih ngeyel: coba pakai selector ini juga */
    div[aria-label="selected option"] {
        background-color: #00A9E0 !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)


st.subheader(
    f"📄 Data Detail for {kota_filter if kota_filter != 'All' else 'All Cities'}")

with st.expander("📁 Pilih Kolom yang Ingin Ditampilkan", expanded=False):
    all_columns = df.columns.tolist()
    selected_columns = st.multiselect(
        "Pilih kolom yang ingin ditampilkan:", all_columns, default=all_columns)

st.dataframe(df[selected_columns])

# ================================
# 9. Interactive Map for FAT Locations using Folium
# ================================
st.subheader("Visualisasi Peta Lokasi FAT ID")

# Input pencarian berdasarkan FAT ID
fat_id_search = st.text_input("Cari FAT ID:", "")

if 'Koordinat FAT' in filtered_df.columns:
    # Copy koordinat ke kolom baru
    filtered_df['Koordinat'] = filtered_df['Koordinat FAT']
    filtered_df = filtered_df.dropna(subset=['Koordinat'])

    # Pisahkan jadi lat dan lon
    filtered_df[['lat', 'lon']] = filtered_df['Koordinat'].str.split(
        ',', expand=True)
    filtered_df['lat'] = pd.to_numeric(filtered_df['lat'], errors='coerce')
    filtered_df['lon'] = pd.to_numeric(filtered_df['lon'], errors='coerce')
    filtered_df = filtered_df.dropna(subset=['lat', 'lon'])

    # Inisialisasi peta dengan fokus ke Jawa Timur
    m = folium.Map(location=[-7.5, 112.5], zoom_start=8)

    # Kalau ada data, sesuaikan dengan lokasi FAT
    if not filtered_df.empty:
        m.fit_bounds(filtered_df[['lat', 'lon']].values.tolist())

    marker_cluster = MarkerCluster().add_to(m)
    found_fat_id = False

    for idx, row in filtered_df.iterrows():
        hc_value = row['TOTAL HC']
        hc_value = "N/A" if pd.isna(hc_value) else str(int(hc_value))

        fat_id_x = row.get('FAT ID X', None)
        if pd.isna(fat_id_x) or str(fat_id_x).strip().lower() in ['', 'none']:
            icon_color = 'green'
            icon_shape = 'ok'
        else:
            icon_color = 'red'
            icon_shape = 'remove'

        marker = folium.Marker(
            location=[row['lat'], row['lon']],
            popup=folium.Popup(
                f"""
                <div style="font-size: 14px; line-height: 1.6; text-align: left; background-color: #f9f9f9; border-radius: 10px; padding: 10px;">
                    <b>Kota/Kab:</b> {row['Kota/Kab']}<br>
                    <b>FAT ID:</b> {row['FATID']}<br>
                    <b>HC:</b> {hc_value}<br>
                    <b>OLT:</b> {row['OLT']}<br>
                    <b>Koordinat FAT:</b> {row['Koordinat FAT']}<br>
                    <b>LINK DOKUMEN FEEDER:</b> <a href="{row['LINK DOKUMEN FEEDER']}" target="_blank" style="color: blue;">Klik di sini</a>
                </div>
                """,
                max_width=300
            ),
            icon=folium.Icon(color=icon_color,
                             icon=icon_shape, prefix='glyphicon')
        )

        if fat_id_search and str(row['FATID']) == fat_id_search:
            marker.add_to(marker_cluster)
            if not found_fat_id:
                m.location = [row['lat'], row['lon']]
                m.zoom_start = 18
                found_fat_id = True
        elif not fat_id_search:
            marker.add_to(marker_cluster)

    if fat_id_search and not found_fat_id:
        st.warning("FAT ID tidak ditemukan. Periksa kembali ID-nya.")

    # Tampilkan peta
    st.write("Peta Lokasi FAT")
    folium_static(m, width=1150, height=600)

    # Menampilkan 10 baris terakhir
    st.subheader("10 Baris Terbaru Berdasarkan Kolom Terakhir")
    last_column = filtered_df.columns[-1]
    last_updated_df = filtered_df.sort_values(
        by=last_column, ascending=False).head(10)
    st.dataframe(last_updated_df)

    # Tombol download
    st.download_button(
        "Ekspor Data ke CSV",
        data=filtered_df.to_csv(index=False),
        file_name="filtered_data.csv",
        mime="text/csv"
    )
else:
    st.warning("Kolom Koordinat FAT tidak ditemukan.")

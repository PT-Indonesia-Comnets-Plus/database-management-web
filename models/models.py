# models.py
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, MetaData
)
# Import tipe data spesifik PostgreSQL jika diperlukan (seperti VECTOR)
from sqlalchemy.dialects.postgresql import VECTOR
from sqlalchemy.orm import relationship, sessionmaker, declarative_base

# Inisialisasi Base dan MetaData
Base = declarative_base()
# Menentukan skema 'public' secara global bisa lebih ringkas
metadata = MetaData(schema="public")
Base.metadata = metadata

# --- Definisi Kelas Model ---


class UserTerminal(Base):
    __tablename__ = 'user_terminals'
    # __table_args__ tidak perlu jika sudah di set di MetaData Base

    # Kolom berdasarkan init.sql
    fat_id = Column(String(255), primary_key=True)
    hostname_olt = Column(String(255))
    latitude_olt = Column(Float)
    longitude_olt = Column(Float)
    brand_olt = Column(String(255))
    type_olt = Column(String(255))
    kapasitas_olt = Column(Integer)
    kapasitas_port_olt = Column(Integer)
    olt_port = Column(Integer)
    olt = Column(String(255))
    interface_olt = Column(String(255))
    fdt_id = Column(String(255))
    status_osp_amarta_fdt = Column(String(255))
    jumlah_splitter_fdt = Column(Integer)
    kapasitas_splitter_fdt = Column(Integer)
    fdt_new_existing = Column(String(255))
    port_fdt = Column(Integer)
    latitude_fdt = Column(Float)
    longitude_fdt = Column(Float)
    jumlah_splitter_fat = Column(Integer)
    kapasitas_splitter_fat = Column(Integer)
    latitude_fat = Column(Float)
    longitude_fat = Column(Float)
    # Kolom ini ada juga di dokumentasis
    status_osp_amarta_fat = Column(String(255))
    fat_kondisi = Column(String(255))
    fat_filter_pemakaian = Column(String(255))
    keterangan_full = Column(String(255))
    fat_id_x = Column(String(255))
    filter_fat_cap = Column(String(255))

    # Relasi (sisi "one" dari one-to-one atau one-to-many)
    # Asumsi relasi ke cluster, home_connected, dokumentasi, additional_info adalah one-to-one
    # karena FK ada di tabel lain dan merujuk ke PK user_terminals (fat_id)
    cluster = relationship("Cluster", back_populates="user_terminal",
                           uselist=False, cascade="all, delete-orphan")
    home_connected = relationship(
        "HomeConnected", back_populates="user_terminal", uselist=False, cascade="all, delete-orphan")
    dokumentasi = relationship(
        "Dokumentasi", back_populates="user_terminal", uselist=False, cascade="all, delete-orphan")
    additional_info = relationship(
        "AdditionalInformation", back_populates="user_terminal", uselist=False, cascade="all, delete-orphan")
    # Relasi ke Pelanggan adalah one-to-many (satu UserTerminal bisa punya banyak Pelanggan)
    pelanggans = relationship(
        "Pelanggan", back_populates="user_terminal", cascade="all, delete-orphan")


class Cluster(Base):
    __tablename__ = 'clusters'

    # Kolom berdasarkan init.sql
    id = Column(Integer, primary_key=True)  # SERIAL -> Integer PK
    latitude_cluster = Column(Float)
    longitude_cluster = Column(Float)
    area_kp = Column(String(255))
    kota_kab = Column(String(255))
    kecamatan = Column(String(255))
    kelurahan = Column(String(255))
    up3 = Column(String(255))
    ulp = Column(String(255))
    # Foreign Key ke user_terminals
    fat_id = Column(String(255), ForeignKey(
        'user_terminals.fat_id', ondelete='CASCADE'), nullable=False)

    # Relasi (sisi "many" atau "one" dari one-to-one)
    user_terminal = relationship("UserTerminal", back_populates="cluster")


class HomeConnected(Base):
    __tablename__ = 'home_connecteds'

    # Kolom berdasarkan init.sql
    id = Column(Integer, primary_key=True)
    hc_old = Column(Integer)
    hc_icrm = Column(Integer)
    total_hc = Column(Integer)
    cleansing_hp = Column(String(255))
    # Foreign Key ke user_terminals
    fat_id = Column(String(255), ForeignKey(
        'user_terminals.fat_id', ondelete='CASCADE'), nullable=False)

    # Relasi
    user_terminal = relationship(
        "UserTerminal", back_populates="home_connected")


class Dokumentasi(Base):
    __tablename__ = 'dokumentasis'

    # Kolom berdasarkan init.sql
    id = Column(Integer, primary_key=True)
    # Kolom ini ada juga di user_terminals
    status_osp_amarta_fat = Column(String(255))
    link_dokumen_feeder = Column(Text)
    keterangan_dokumen = Column(Text)
    link_data_aset = Column(Text)
    keterangan_data_aset = Column(Text)
    link_maps = Column(Text)
    update_aset = Column(String(255))
    amarta_update = Column(String(255))
    # Foreign Key ke user_terminals
    fat_id = Column(String(255), ForeignKey(
        'user_terminals.fat_id', ondelete='CASCADE'), nullable=False)

    # Relasi
    user_terminal = relationship("UserTerminal", back_populates="dokumentasi")


class AdditionalInformation(Base):
    __tablename__ = 'additional_informations'

    # Kolom berdasarkan init.sql
    id = Column(Integer, primary_key=True)
    pa = Column(String(255))
    tanggal_rfs = Column(Date)
    mitra = Column(String(255))
    kategori = Column(String(255))
    sumber_datek = Column(String(255))
    # Foreign Key ke user_terminals
    fat_id = Column(String(255), ForeignKey(
        'user_terminals.fat_id', ondelete='CASCADE'), nullable=False)

    # Relasi
    user_terminal = relationship(
        "UserTerminal", back_populates="additional_info")


class Pelanggan(Base):
    __tablename__ = 'pelanggans'

    # Kolom berdasarkan init.sql
    id_permohonan = Column(String(255), primary_key=True)
    sid = Column(String(255))
    cust_name = Column(String(255))
    telpn = Column(String(255))
    latitude_pelanggan = Column(Float)
    longitude_pelanggan = Column(Float)
    # Foreign Key ke user_terminals
    fat_id = Column(String(255), ForeignKey(
        'user_terminals.fat_id', ondelete='CASCADE'), nullable=False)
    notes = Column(Text)

    # Relasi (sisi "many" dari one-to-many)
    user_terminal = relationship("UserTerminal", back_populates="pelanggans")


# --- Model untuk Chatbot (jika tabel 'documents' ada) ---
# Pastikan tabel 'documents' memang ada di database Anda dengan struktur ini
# dan Anda telah menginstal ekstensi pgvector serta library sqlalchemy-pgvector
# pip install sqlalchemy-pgvector
class DocumentEmbedding(Base):
    __tablename__ = 'documents'
    # __table_args__ = {'schema': 'public'} # Sudah di set di MetaData Base

    id = Column(Integer, primary_key=True)
    content = Column(Text)
    # Pertimbangkan menggunakan JSONB jika metadata Anda terstruktur
    # from sqlalchemy.dialects.postgresql import JSONB
    # metadata = Column(JSONB)
    metadata = Column(Text)
    # Pastikan dimensi vektor (1536) sesuai dengan model embedding Anda
    embedding = Column(VECTOR(1536))


# --- Setup Engine dan Session (Contoh) ---
# Letakkan ini di file konfigurasi atau file utama aplikasi Anda

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# DATABASE_URL = "postgresql+psycopg2://user:password@host:port/database"
# # Ganti 'user', 'password', 'host', 'port', 'database' dengan detail koneksi Anda

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fungsi untuk mendapatkan sesi database (berguna dalam aplikasi web/API)
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# Untuk membuat semua tabel berdasarkan model ini (jika belum ada)
# Panggil ini sekali saat inisialisasi aplikasi jika diperlukan
# Base.metadata.create_all(bind=engine)

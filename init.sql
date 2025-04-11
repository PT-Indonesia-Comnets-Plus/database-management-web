CREATE TABLE olts (
    id SERIAL PRIMARY KEY,
    hostname_olt VARCHAR(255),
    latitude_olt FLOAT,
    longitude_olt FLOAT,
    brand_olt VARCHAR(255),
    type_olt VARCHAR(255),
    kapasitas_olt INTEGER,
    kapasitas_port_olt INTEGER,
    olt_port INTEGER,
    olt VARCHAR(255),
    interface_olt VARCHAR(255)
);

CREATE TABLE fdts (
    id SERIAL PRIMARY KEY,
    fdt_id VARCHAR(255),
    status_osp_amarta_fdt VARCHAR(255),
    jumlah_splitter_fdt INTEGER,
    kapasitas_splitter_fdt INTEGER,
    fdt_new_existing VARCHAR(255),
    port_fdt INTEGER,
    latitude_fdt FLOAT,
    longitude_fdt FLOAT,
    olt_id INTEGER REFERENCES olts(id) ON DELETE CASCADE
);

CREATE TABLE fats (
    id SERIAL PRIMARY KEY,
    fatid VARCHAR(255),
    jumlah_splitter_fat INTEGER,
    kapasitas_splitter_fat INTEGER,
    latitude_fat FLOAT,
    longitude_fat FLOAT,
    fdt_id INTEGER REFERENCES fdts(id) ON DELETE CASCADE,
    status_osp_amarta_fat VARCHAR(255),
    fat_kondisi VARCHAR(255),
    fat_filter_pemakaian VARCHAR(255),
    keterangan_full VARCHAR(255),
    fatid_x VARCHAR(255),
    filter_fat_cap VARCHAR(255)
);

CREATE TABLE pelanggans (
    id SERIAL PRIMARY KEY,
    id_permohonan VARCHAR(255),
    sid VARCHAR(255),
    cust_name VARCHAR(255),
    telpn VARCHAR(255),
    latitude_pelanggan FLOAT,
    longitude_pelanggan FLOAT,
    fat_id INTEGER REFERENCES fats(id) ON DELETE CASCADE,
    notes TEXT
);

CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    latitude_cluster FLOAT,
    longitude_cluster FLOAT,
    area_kp VARCHAR(255),
    kota_kab VARCHAR(255),
    kecamatan VARCHAR(255),
    kelurahan VARCHAR(255),
    up3 VARCHAR(255),
    ulp VARCHAR(255),
    fat_id INTEGER REFERENCES fats(id) ON DELETE CASCADE
);

CREATE TABLE home_connecteds (
    id SERIAL PRIMARY KEY,
    hc_old INTEGER,
    hc_icrm INTEGER,
    total_hc INTEGER,
    cleansing_hp VARCHAR(255),
    fat_id INTEGER REFERENCES fats(id) ON DELETE CASCADE
);

CREATE TABLE dokumentasis (
    id SERIAL PRIMARY KEY,
    status_osp_amarta_fat VARCHAR(255),
    link_dokumen_feeder TEXT,
    keterangan_dokumen TEXT,
    link_data_aset TEXT,
    keterangan_data_aset TEXT,
    link_maps TEXT,
    update_aset VARCHAR(255),
    amarta_update VARCHAR(255),
    fat_id INTEGER REFERENCES fats(id) ON DELETE CASCADE
);

CREATE TABLE additional_informations (
    id SERIAL PRIMARY KEY,
    pa VARCHAR(255),
    tanggal_rfs DATE,
    mitra VARCHAR(255),
    kategori VARCHAR(255),
    sumber_datek VARCHAR(255),
    fat_id INTEGER REFERENCES fats(id) ON DELETE CASCADE
);
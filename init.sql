-- Tabel utama: fiber_network
CREATE TABLE user_terminals (
    fat_id VARCHAR(255) PRIMARY KEY, 
    hostname_olt VARCHAR(255),
    latitude_olt FLOAT,
    longitude_olt FLOAT,
    brand_olt VARCHAR(255),
    type_olt VARCHAR(255),
    kapasitas_olt INTEGER,
    kapasitas_port_olt INTEGER,
    olt_port INTEGER,
    olt VARCHAR(255),
    interface_olt VARCHAR(255),
    fdt_id VARCHAR(255),
    status_osp_amarta_fdt VARCHAR(255),
    jumlah_splitter_fdt INTEGER,
    kapasitas_splitter_fdt INTEGER,
    fdt_new_existing VARCHAR(255),
    port_fdt INTEGER,
    latitude_fdt FLOAT,
    longitude_fdt FLOAT,
    jumlah_splitter_fat INTEGER,
    kapasitas_splitter_fat INTEGER,
    latitude_fat FLOAT,
    longitude_fat FLOAT,
    status_osp_amarta_fat VARCHAR(255),
    fat_kondisi VARCHAR(255),
    fat_filter_pemakaian VARCHAR(255),
    keterangan_full VARCHAR(255),
    fat_id_x VARCHAR(255),
    filter_fat_cap VARCHAR(255)
);

-- Tabel clusters
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
    fat_id VARCHAR(255) NOT NULL REFERENCES user_terminals(fat_id) ON DELETE CASCADE
);

-- Tabel home_connecteds
CREATE TABLE home_connecteds (
    id SERIAL PRIMARY KEY,
    hc_old INTEGER,
    hc_icrm INTEGER,
    total_hc INTEGER,
    cleansing_hp VARCHAR(255),
    fat_id VARCHAR(255) NOT NULL REFERENCES user_terminals(fat_id) ON DELETE CASCADE
);

-- Tabel dokumentasis
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
    fat_id VARCHAR(255) NOT NULL REFERENCES user_terminals(fat_id) ON DELETE CASCADE
);

-- Tabel additional_informations
CREATE TABLE additional_informations (
    id SERIAL PRIMARY KEY,
    pa VARCHAR(255),
    tanggal_rfs DATE,
    mitra VARCHAR(255),
    kategori VARCHAR(255),
    sumber_datek VARCHAR(255),
    fat_id VARCHAR(255) NOT NULL REFERENCES user_terminals(fat_id) ON DELETE CASCADE
);

-- Tabel pelanggan
CREATE TABLE pelanggans (
    id_permohonan VARCHAR(255) PRIMARY KEY, 
    sid VARCHAR(255), 
    cust_name VARCHAR(255), 
    telpn VARCHAR(255), 
    latitude_pelanggan FLOAT, 
    longitude_pelanggan FLOAT,
    fat_id VARCHAR(255) NOT NULL REFERENCES user_terminals(fat_id) ON DELETE CASCADE, -- Relasi ke fiber_network
    notes TEXT 
);

-- Tabel documents untuk RAG system (PDF embeddings)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata TEXT, -- JSON string containing file metadata
    embedding vector(1536) -- Google embedding model dimensions
);

-- Index untuk faster similarity search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Tabel documents untuk RAG system (PDF embeddings)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata TEXT, -- JSON string containing file metadata
    embedding vector(1536) -- Google embedding model dimensions
);

-- Index untuk faster similarity search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- DYNAMIC COLUMNS METADATA SYSTEM
-- ============================================

-- Table untuk menyimpan metadata kolom dinamis
CREATE TABLE IF NOT EXISTS dynamic_columns (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(50) NOT NULL DEFAULT 'TEXT',
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_searchable BOOLEAN DEFAULT TRUE,
    default_value TEXT,
    validation_rules JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(table_name, column_name)
);

-- Table untuk menyimpan data kolom dinamis
CREATE TABLE IF NOT EXISTS dynamic_column_data (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(255) NOT NULL, -- Reference ke fat_id atau primary key lain
    column_id INTEGER REFERENCES dynamic_columns(id) ON DELETE CASCADE,
    column_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(record_id, column_id)
);

-- Index untuk performa
CREATE INDEX IF NOT EXISTS idx_dynamic_column_data_record_id ON dynamic_column_data(record_id);
CREATE INDEX IF NOT EXISTS idx_dynamic_column_data_column_id ON dynamic_column_data(column_id);
CREATE INDEX IF NOT EXISTS idx_dynamic_columns_table_active ON dynamic_columns(table_name, is_active);

-- Trigger untuk update timestamp
CREATE OR REPLACE FUNCTION update_dynamic_column_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_dynamic_column_data_updated_at
    BEFORE UPDATE ON dynamic_column_data
    FOR EACH ROW
    EXECUTE FUNCTION update_dynamic_column_timestamp();

-- Sample data untuk testing
INSERT INTO dynamic_columns (table_name, column_name, display_name, description, column_type, is_searchable) 
VALUES 
    ('user_terminals', 'custom_status', 'Status Khusus', 'Status khusus untuk monitoring', 'TEXT', true),
    ('user_terminals', 'maintenance_date', 'Tanggal Maintenance', 'Tanggal maintenance terakhir', 'DATE', true),
    ('user_terminals', 'priority_level', 'Level Prioritas', 'Level prioritas untuk maintenance', 'INTEGER', true)
ON CONFLICT (table_name, column_name) DO NOTHING;
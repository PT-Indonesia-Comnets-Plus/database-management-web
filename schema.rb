ActiveRecord::Schema.define(version: 2025_04_09_000000) do

  # Tabel utama: user_terminals (menggabungkan semua informasi OLT, FDT, dan FAT)
  create_table "user_terminals", primary_key: "fat_id", id: :string, limit: 255, force: :cascade do |t|
    t.string "hostname_olt", limit: 255
    t.float "latitude_olt"
    t.float "longitude_olt"
    t.string "brand_olt", limit: 255
    t.string "type_olt", limit: 255
    t.integer "kapasitas_olt"
    t.integer "kapasitas_port_olt"
    t.integer "olt_port"
    t.string "olt", limit: 255
    t.string "interface_olt", limit: 255
    t.string "fdt_id", limit: 255
    t.string "status_osp_amarta_fdt", limit: 255
    t.integer "jumlah_splitter_fdt"
    t.integer "kapasitas_splitter_fdt"
    t.string "fdt_new_existing", limit: 255
    t.integer "port_fdt"
    t.float "latitude_fdt"
    t.float "longitude_fdt"
    t.integer "jumlah_splitter_fat"
    t.integer "kapasitas_splitter_fat"
    t.float "latitude_fat"
    t.float "longitude_fat"
    t.string "status_osp_amarta_fat", limit: 255
    t.string "fat_kondisi", limit: 255
    t.string "fat_filter_pemakaian", limit: 255
    t.string "keterangan_full", limit: 255
    t.string "fat_id_x", limit: 255
    t.string "filter_fat_cap", limit: 255
  end

  # Tabel clusters
  create_table "clusters", id: :serial, force: :cascade do |t|
    t.float "latitude_cluster"
    t.float "longitude_cluster"
    t.string "area_kp", limit: 255
    t.string "kota_kab", limit: 255
    t.string "kecamatan", limit: 255
    t.string "kelurahan", limit: 255
    t.string "up3", limit: 255
    t.string "ulp", limit: 255
    t.string "fat_id", limit: 255, null: false
    t.foreign_key "user_terminals", column: "fat_id", primary_key: "fat_id", on_delete: :cascade
  end

  # Tabel home_connecteds
  create_table "home_connecteds", id: :serial, force: :cascade do |t|
    t.integer "hc_old"
    t.integer "hc_icrm"
    t.integer "total_hc"
    t.string "cleansing_hp", limit: 255
    t.string "fat_id", limit: 255, null: false
    t.foreign_key "user_terminals", column: "fat_id", primary_key: "fat_id", on_delete: :cascade
  end

  # Tabel dokumentasis
  create_table "dokumentasis", id: :serial, force: :cascade do |t|
    t.string "status_osp_amarta_fat", limit: 255
    t.text "link_dokumen_feeder"
    t.text "keterangan_dokumen"
    t.text "link_data_aset"
    t.text "keterangan_data_aset"
    t.text "link_maps"
    t.string "update_aset", limit: 255
    t.string "amarta_update", limit: 255
    t.string "fat_id", limit: 255, null: false
    t.foreign_key "user_terminals", column: "fat_id", primary_key: "fat_id", on_delete: :cascade
  end

  # Tabel additional_informations
  create_table "additional_informations", id: :serial, force: :cascade do |t|
    t.string "pa", limit: 255
    t.date "tanggal_rfs"
    t.string "mitra", limit: 255
    t.string "kategori", limit: 255
    t.string "sumber_datek", limit: 255
    t.string "fat_id", limit: 255, null: false
    t.foreign_key "user_terminals", column: "fat_id", primary_key: "fat_id", on_delete: :cascade
  end

  # Tabel pelanggans
  create_table "pelanggans", primary_key: "id_permohonan", id: :string, limit: 255, force: :cascade do |t|
    t.string "sid", limit: 255
    t.string "cust_name", limit: 255
    t.string "telpn", limit: 255
    t.float "latitude_pelanggan"
    t.float "longitude_pelanggan"
    t.string "fat_id", limit: 255, null: false
    t.text "notes"
    t.foreign_key "user_terminals", column: "fat_id", primary_key: "fat_id", on_delete: :cascade
  end

end
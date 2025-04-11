ActiveRecord::Schema.define(version: 2025_04_09_000000) do

    create_table "olts", id: :serial, force: :cascade do |t|
      t.string "hostname_olt"
      t.float "latitude_olt"
      t.float "longitude_olt"
      t.string "brand_olt"
      t.string "type_olt"
      t.integer "kapasitas_olt"
      t.integer "kapasitas_port_olt"
      t.integer "olt_port"
      t.string "olt"
      t.string "interface_olt"
      t.timestamps
    end
  
    create_table "fdts", id: :serial, force: :cascade do |t|
      t.string "fdt_id"
      t.string "status_osp_amarta_fdt"
      t.integer "jumlah_splitter_fdt"
      t.integer "kapasitas_splitter_fdt"
      t.string "fdt_new_existing"
      t.integer "port_fdt"
      t.float "latitude_fdt"
      t.float "longitude_fdt"
      t.references "olt", foreign_key: true, null: false, on_delete: :cascade
      t.timestamps
    end
  
    create_table "fats", id: :serial, force: :cascade do |t|
      t.string "fatid"
      t.integer "jumlah_splitter_fat"
      t.integer "kapasitas_splitter_fat"
      t.float "latitude_fat"
      t.float "longitude_fat"
      t.references "fdt", foreign_key: true, null: false, on_delete: :cascade
      t.string "status_osp_amarta_fat"
      t.string "fat_kondisi"
      t.string "fat_filter_pemakaian"
      t.string "keterangan_full"
      t.string "fatid_x"
      t.string "filter_fat_cap"
      t.timestamps
    end
  
    create_table "pelanggans", id: :serial, force: :cascade do |t|
      t.string "id_permohonan"
      t.string "sid"
      t.string "cust_name"
      t.string "telpn"
      t.float "latitude_pelanggan"
      t.float "longitude_pelanggan"
      t.references "fat", foreign_key: true, null: false, on_delete: :cascade
      t.string "notes"
      t.timestamps
    end
  
    create_table "clusters", id: :serial, force: :cascade do |t|
      t.float "latitude_cluster"
      t.float "longitude_cluster"
      t.string "area_kp"
      t.string "kota_kab"
      t.string "kecamatan"
      t.string "kelurahan"
      t.string "up3"
      t.string "ulp"
      t.references "fat", foreign_key: true, null: false, on_delete: :cascade
      t.timestamps
    end
  
    create_table "home_connecteds", id: :serial, force: :cascade do |t|
      t.integer "hc_old"
      t.integer "hc_icrm"
      t.integer "total_hc"
      t.string "cleansing_hp"
      t.references "fat", foreign_key: true, null: false, on_delete: :cascade
      t.timestamps
    end
  
    create_table "dokumentasis", id: :serial, force: :cascade do |t|
      t.string "status_osp_amarta_fat"
      t.string "link_dokumen_feeder"
      t.string "keterangan_dokumen"
      t.string "link_data_aset"
      t.string "keterangan_data_aset"
      t.string "link_maps"
      t.string "update_aset"
      t.string "amarta_update"
      t.references "fat", foreign_key: true, null: false, on_delete: :cascade
      t.timestamps
    end
  
    create_table "additional_informations", id: :serial, force: :cascade do |t|
      t.string "pa"
      t.date "tanggal_rfs"
      t.string "mitra"
      t.string "kategori"
      t.string "sumber_datek"
      t.references "fat", foreign_key: true, null: false, on_delete: :cascade
      t.timestamps
    end
  
  end
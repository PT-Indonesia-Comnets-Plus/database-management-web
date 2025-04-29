# core/services/AssetDataService.py

import pandas as pd
import streamlit as st
from psycopg2 import pool, Error as Psycopg2Error
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import re
from datetime import date
from core.helper.load_data_configs import load_data_config


class AssetDataService:
    """
    Service class for managing asset data interactions with the database.
    Handles loading, inserting, updating, deleting, and processing asset data.
    """

    def __init__(self, db_pool: pool.SimpleConnectionPool):
        """
        Initializes the AssetDataService.

        Args:
            db_pool: The psycopg2 connection pool.
        """
        if db_pool is None:
            raise ValueError(
                "Database connection pool (db_pool) cannot be None.")
        self.db_pool = db_pool

    def _execute_query(self, query: str, params: Optional[tuple] = None, fetch: str = "all") -> Tuple[Optional[List[Tuple]], Optional[List[str]], Optional[str]]:
        """
        Executes a SQL query using the connection pool.

        Args:
            query: The SQL query string.
            params: Optional tuple of parameters for the query.
            fetch: Type of fetch operation ('all', 'one', 'none').

        Returns:
            A tuple containing (data, column_names, error_message).
            data is None if error or fetch='none'.
            column_names is None if error or no description.
            error_message is None if successful.
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch == "all" and cur.description:
                    data = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return data, columns, None
                elif fetch == "one" and cur.description:
                    data = cur.fetchone()
                    columns = [desc[0] for desc in cur.description]
                    # Return as list for consistency
                    return [data] if data else [], columns, None
                elif fetch == "none":
                    conn.commit()
                    return [], [], f"Query executed (rows affected: {cur.rowcount})"
                else:  # Non-SELECT query without explicit fetch='none'
                    conn.commit()
                    return [], [], f"Non-SELECT query executed (rows affected: {cur.rowcount})"
        except Psycopg2Error as db_err:
            if conn:
                conn.rollback()
            return None, None, f"Database Error: {db_err}"
        except Exception as e:
            if conn:
                conn.rollback()
            return None, None, f"Execution Error: {e}"
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def load_all_assets(self, limit: Optional[int] = 50) -> Optional[pd.DataFrame]:
        """
        Loads asset data by joining relevant tables.

        Args:
            limit: Maximum number of rows to load. Defaults to 50.

        Returns:
            A pandas DataFrame containing the asset data, or None if an error occurs.
        """
        query = """
            SELECT
                ut.fat_id, ut.hostname_olt, ut.latitude_olt, ut.longitude_olt, ut.brand_olt, ut.type_olt,
                ut.kapasitas_olt, ut.kapasitas_port_olt, ut.olt_port, ut.olt, ut.interface_olt,
                ut.fdt_id, ut.status_osp_amarta_fdt, ut.jumlah_splitter_fdt, ut.kapasitas_splitter_fdt,
                ut.fdt_new_existing, ut.port_fdt, ut.latitude_fdt, ut.longitude_fdt,
                ut.jumlah_splitter_fat, ut.kapasitas_splitter_fat, ut.latitude_fat, ut.longitude_fat,
                ut.status_osp_amarta_fat, ut.fat_kondisi, ut.fat_filter_pemakaian, ut.keterangan_full,
                ut.fat_id_x, ut.filter_fat_cap,
                cl.latitude_cluster, cl.longitude_cluster, cl.area_kp, cl.kota_kab, cl.kecamatan,
                cl.kelurahan, cl.up3, cl.ulp,
                hc.hc_old, hc.hc_icrm, hc.total_hc, hc.cleansing_hp,
                dk.status_osp_amarta_fat AS dk_status_osp_amarta_fat, dk.link_dokumen_feeder,
                dk.keterangan_dokumen, dk.link_data_aset, dk.keterangan_data_aset, dk.link_maps,
                dk.update_aset, dk.amarta_update,
                ai.pa, ai.tanggal_rfs, ai.mitra, ai.kategori, ai.sumber_datek
            FROM user_terminals ut
            LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
            LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
            LEFT JOIN dokumentasis dk ON ut.fat_id = dk.fat_id
            LEFT JOIN additional_informations ai ON ut.fat_id = ai.fat_id
            LIMIT %s;
        """
        data, columns, error = self._execute_query(
            query, (limit,), fetch="all")
        if error:
            st.error(f"Failed to load asset data: {error}")
            return None
        if data is None:  # Should not happen if error is None, but check anyway
            st.warning("No asset data returned from query.")
            # Return empty DF with columns if possible
            return pd.DataFrame(columns=columns or [])
        return pd.DataFrame(data, columns=columns)

    def search_assets(self, column_name: str, value: Any) -> Optional[pd.DataFrame]:
        """
        Searches for assets based on a specific column and value.

        Args:
            column_name: The name of the column to search in (e.g., "FATID", "FDTID").
            value: The value to search for.

        Returns:
            A pandas DataFrame containing the matching assets, or None if an error occurs.
        """
        # Basic validation to prevent SQL injection (use parameterized query)
        # Further validation might be needed depending on allowed column_names
        allowed_columns = ["FATID", "FDTID", "OLT",
                           "fat_id", "fdt_id", "olt"]  # Add more if needed
        # Use lower case for internal query consistency if DB columns are lower case
        db_column_name = column_name.lower()
        if db_column_name not in allowed_columns:
            st.error(f"Invalid search column: {column_name}")
            return None

        # Assuming all tables use 'fat_id' as a common key if joining is needed later
        # For now, search only in user_terminals for simplicity, adjust if needed
        query = f'SELECT * FROM user_terminals WHERE "{db_column_name}" = %s'

        data, columns, error = self._execute_query(
            query, (value,), fetch="all")

        if error:
            st.error(f"Failed to search assets: {error}")
            return None
        if data is None:
            st.warning("No asset data returned from search query.")
            return pd.DataFrame(columns=columns or [])
        return pd.DataFrame(data, columns=columns)

    def process_uploaded_asset_file(self, uploaded_file) -> Optional[pd.DataFrame]:
        """
        Processes an uploaded asset file (CSV assumed).
        Applies cleaning, renaming, type conversion, and coordinate splitting.

        Args:
            uploaded_file: The file object from st.file_uploader.

        Returns:
            A processed pandas DataFrame, or None if an error occurs.
        """
        try:
            # Load file CSV ke DataFrame
            df = pd.read_csv(uploaded_file)

            # Rename columns untuk standarisasi nama kolom
            df.rename(columns={
                "Kordinat OLT": "Koordinat OLT",
                "Koodinat FDT": "Koordinat FDT",
                "Koordinat Cluster": "Koordinat Cluster",
                "Koodinat FAT": "Koordinat FAT"
            }, inplace=True)

            # Split koordinat ke kolom latitude dan longitude
            coordinate_columns = {
                "Koordinat OLT": ("Latitude OLT", "Longitude OLT"),
                "Koordinat FDT": ("Latitude FDT", "Longitude FDT"),
                "Koordinat Cluster": ("Latitude Cluster", "Longitude Cluster"),
                "Koordinat FAT": ("Latitude FAT", "Longitude FAT")
            }
            for coord_col, (lat_col, lon_col) in coordinate_columns.items():
                if coord_col in df.columns:
                    df[[lat_col, lon_col]] = df[coord_col].str.split(
                        ",", expand=True)
                    df.drop(columns=[coord_col], inplace=True)

            # Fill default values untuk kolom tertentu
            df.fillna({
                "Jumlah Splitter FDT": 0,
                "Kapasitas Splitter FDT": 0,
                "Jumlah Splitter FAT": 0,
                "Kapasitas Splitter FAT": 0,
                "Kapasitas OLT": 0,
                "Kapasitas port OLT": 0,
                "OLT Port": 0,
                "Port FDT": 0,
                "HC OLD": 0,
                "HC iCRM+": 0,
                "TOTAL HC": 0
            }, inplace=True)

            # Drop kolom original koordinat jika masih ada
            df.drop(columns=["koordinat_olt", "koordinat_fdt", "koordinat_cluster", "koordinat_fat"],
                    errors="ignore", inplace=True)

            # Load konfigurasi tipe data dari YAML
            try:
                # --- Panggil fungsi yang benar ---
                table_configs = load_data_config()  # Panggil fungsi yang sudah diimpor
                # ---------------------------------
                if not table_configs:
                    st.error(
                        "Failed to load data configuration (data_config.yml). Cannot proceed with type conversion.")
                    return None
                flat_astype_map = {}
                for table, columns in table_configs.items():
                    flat_astype_map.update(columns)
                st.write("Loaded data type configuration.")
            except FileNotFoundError:
                st.error("Configuration file 'data_config.yml' not found.")
                return None
            except Exception as e:
                st.error(f"Error loading or parsing 'data_config.yml': {e}")
                return None

            return df

        except pd.errors.ParserError as e:
            st.error(f"Failed to parse uploaded file: {e}")
            return None
        except Exception as e:
            st.error(
                f"An unexpected error occurred during file processing: {e}")
            return None

    def insert_asset_dataframe(self, df: pd.DataFrame) -> Tuple[int, int]:
        """
        Inserts data from a DataFrame into the respective asset tables.
        This requires splitting the DataFrame first based on the target table schema.

        Args:
            df: The processed DataFrame containing combined asset data.

        Returns:
            Tuple (inserted_count, error_count).
        """
        inserted_count = 0
        error_count = 0

        # Define columns for each target table (must match DB schema)
        table_columns = {
            # Add all columns
            "user_terminals": ["fat_id", "hostname_olt", "latitude_olt", "longitude_olt", ...],
            # Add all columns
            "clusters": ["fat_id", "latitude_cluster", "longitude_cluster", ...],
            # Add all columns
            "home_connecteds": ["fat_id", "hc_old", "hc_icrm", ...],
            # Add all columns
            "dokumentasis": ["fat_id", "status_osp_amarta_fat", "link_dokumen_feeder", ...],
            # Add all columns
            "additional_informations": ["fat_id", "pa", "tanggal_rfs", ...]
        }

        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cur:
                for table_name, columns in table_columns.items():
                    # Select only the relevant columns from the input DataFrame
                    df_subset = df[[
                        col for col in columns if col in df.columns]].copy()
                    # Drop duplicates based on primary/unique keys if necessary before insert
                    if table_name == "user_terminals":
                        df_subset.drop_duplicates(
                            subset=['fat_id'], keep='first', inplace=True)
                    # Add similar logic for other tables if they have unique constraints

                    if df_subset.empty:
                        st.info(f"No data to insert into '{table_name}'.")
                        continue

                    st.info(
                        f"Inserting {len(df_subset)} rows into '{table_name}'...")
                    cols_str = ", ".join(
                        [f'"{col}"' for col in df_subset.columns])
                    placeholders = ", ".join(["%s"] * len(df_subset.columns))
                    insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
                    # Handle ON CONFLICT for updates if needed, e.g., ON CONFLICT (fat_id) DO UPDATE SET ...

                    # Convert DataFrame rows to list of tuples, handling NaT/NaN
                    data_tuples = [
                        tuple(None if pd.isna(x) else x for x in row)
                        for row in df_subset.itertuples(index=False, name=None)
                    ]

                    try:
                        cur.executemany(insert_query, data_tuples)
                        inserted_count += cur.rowcount  # executemany might not return accurate count easily
                        # Simplified success message
                        st.success(f"Inserted data into '{table_name}'.")
                    except Psycopg2Error as insert_err:
                        conn.rollback()  # Rollback this batch
                        st.error(
                            f"Error inserting into '{table_name}': {insert_err}")
                        # Assume all failed in batch
                        error_count += len(data_tuples)
                        # Optionally break or continue to next table
                        continue  # Continue to next table

                conn.commit()  # Commit successful insertions

        except Exception as e:
            if conn:
                conn.rollback()
            st.error(f"General error during DataFrame insertion: {e}")
            # Hard to estimate error_count here
        finally:
            if conn:
                self.db_pool.putconn(conn)

        return inserted_count, error_count

    def insert_single_asset(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Inserts a single asset record provided as a dictionary.
        This is complex as data needs to be split and inserted into multiple tables.
        Consider using insert_asset_dataframe with a single-row DataFrame instead.

        Args:
            data: Dictionary representing a single asset record.

        Returns:
            Error message string if failed, None if successful.
        """
        # This function is complex due to multi-table inserts and transactions.
        # It's generally easier to create a single-row DataFrame and use insert_asset_dataframe.
        st.warning(
            "insert_single_asset is complex. Consider using insert_asset_dataframe.")
        # Placeholder implementation:
        df = pd.DataFrame([data])
        _, error_count = self.insert_asset_dataframe(df)
        return "Insertion failed" if error_count > 0 else None

    def update_asset(self, identifier_col: str, identifier_value: Any, update_data: Dict[str, Any]) -> Optional[str]:
        """
        Updates a single asset record identified by a key column and value.
        Currently updates only the 'user_terminals' table. Extend if needed.

        Args:
            identifier_col: The column name to identify the record (e.g., "fat_id").
            identifier_value: The value of the identifier column.
            update_data: Dictionary of columns and their new values.

        Returns:
            Error message string if failed, None if successful.
        """
        if not update_data:
            return "No update data provided."

        # Assume updates target user_terminals for now
        table_name = "user_terminals"
        db_identifier_col = identifier_col.lower()  # Ensure lowercase if DB uses it

        set_clause = ", ".join([f'"{col}" = %s' for col in update_data.keys()])
        values = list(update_data.values()) + [identifier_value]
        query = f'UPDATE {table_name} SET {set_clause} WHERE "{db_identifier_col}" = %s'

        _, _, error = self._execute_query(query, tuple(values), fetch="none")

        if error:
            st.error(f"Failed to update asset: {error}")
            return f"Update Error: {error}"
        return None  # Success

    def delete_asset(self, identifier_col: str, identifier_value: Any) -> Optional[str]:
        """
        Deletes asset records based on an identifier.
        Handles cascading deletes if set up in DB, otherwise deletes only from specified tables.

        Args:
            identifier_col: The column name to identify the record (e.g., "fat_id").
            identifier_value: The value of the identifier column.

        Returns:
            Error message string if failed, None if successful.
        """
        # Important: Deleting requires careful handling of foreign key relationships.
        # Option 1: Rely on DB's ON DELETE CASCADE (if configured). Delete only from parent table.
        # Option 2: Manually delete from child tables first, then parent.

        # Assuming Option 1 (delete from parent 'user_terminals')
        table_name = "user_terminals"
        db_identifier_col = identifier_col.lower()

        query = f'DELETE FROM {table_name} WHERE "{db_identifier_col}" = %s'
        _, _, error = self._execute_query(
            query, (identifier_value,), fetch="none")

        if error:
            st.error(f"Failed to delete asset: {error}")
            return f"Deletion Error: {error}"

        # Add manual deletes for child tables if Option 2 is needed
        # child_tables = ["clusters", "home_connecteds", "dokumentasis", "additional_informations", "pelanggans"]
        # for child_table in child_tables:
        #     query_child = f'DELETE FROM {child_table} WHERE "{db_identifier_col}" = %s'
        #     _, _, error_child = self._execute_query(query_child, (identifier_value,), fetch="none")
        #     if error_child:
        #         st.warning(f"Could not delete from child table {child_table}: {error_child}")
        #         # Decide whether to stop or continue

        return None  # Success

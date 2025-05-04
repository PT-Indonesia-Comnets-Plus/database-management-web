# core/services/AssetDataService.py

import pandas as pd
import streamlit as st
from psycopg2 import pool, Error as Psycopg2Error
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from etl_proces import AssetPipeline
import asyncio


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
                    return [data] if data else [], columns, None
                elif fetch == "none":
                    conn.commit()
                    return [], [], f"Query executed (rows affected: {cur.rowcount})"
                else:
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

    def load_all_assets(self, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Loads essential asset data for the dashboard by joining relevant tables.

        Args:
            limit: Maximum number of rows to load. If None, loads all.

        Returns:
            A pandas DataFrame containing the essential asset data, or None if an error occurs.
        """
        # --- MODIFIKASI QUERY ---
        query = """
            SELECT
                ut.fat_id,          -- Kunci join dan digunakan di KPI/Map
                ut.olt,             -- Digunakan di KPI/Map
                ut.fdt_id,          -- Digunakan di KPI
                ut.brand_olt,       -- Digunakan di Visualisasi
                ut.fat_filter_pemakaian, -- Digunakan di Visualisasi
                ut.latitude_fat,    -- Untuk Peta
                ut.longitude_fat,   -- Untuk Peta
                ut.fat_id_x,        -- Untuk ikon Peta
                cl.kota_kab,        -- Digunakan di Filter, KPI, Visualisasi, Map
                hc.total_hc,        -- Digunakan di KPI, Visualisasi, Map, Bump Chart
                dk.link_dokumen_feeder, -- Untuk popup Peta
                ai.tanggal_rfs      -- <<< BARU: Untuk Bump Chart
            FROM user_terminals ut
            LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
            LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
            LEFT JOIN dokumentasis dk ON ut.fat_id = dk.fat_id
            LEFT JOIN additional_informations ai ON ut.fat_id = ai.fat_id -- <<< BARU: Join untuk tanggal RFS
        """
        query_params = []
        if limit is not None:
            query += " LIMIT %s"
            query_params.append(limit)
        query += ";"

        data, columns, error = self._execute_query(
            query, tuple(query_params) if query_params else None, fetch="all")

        if error:
            st.error(f"Failed to load asset data: {error}")
            return None
        if data is None:
            st.warning("No asset data returned from query.")
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
        allowed_columns = ["FATID", "FDTID", "OLT",
                           "fat_id", "fdt_id", "olt"]

        db_column_name = column_name.lower()
        if db_column_name not in allowed_columns:
            st.error(f"Invalid search column: {column_name}")
            return None

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

    def _get_existing_fat_ids(self) -> Tuple[Optional[set], Optional[str]]:
        """
        Fetches distinct, cleaned (stripped, uppercase) FAT IDs from the user_terminals table.

        Returns:
            A tuple containing (set_of_fat_ids, error_message).
            set_of_fat_ids is None if an error occurs.
            error_message is None if successful.
        """
        print("DEBUG: Fetching existing FAT IDs from database...")
        query_existing = "SELECT DISTINCT fat_id FROM user_terminals;"
        existing_data, _, db_error = self._execute_query(
            query_existing, fetch="all")

        if db_error:
            return None, f"Failed to fetch existing FAT IDs: {db_error}"

        db_fat_id_set = set()
        if existing_data:
            db_fat_id_set = {str(item[0]).strip().upper()
                             for item in existing_data if item[0] is not None}
            print(
                f"DEBUG: Found {len(db_fat_id_set)} unique existing FAT IDs.")
        else:
            print("DEBUG: No existing FAT IDs found in database.")
        return db_fat_id_set, None

    def _filter_new_records(self, df: pd.DataFrame, existing_ids: set) -> pd.DataFrame:
        """Filters a DataFrame to keep only rows with fat_id not present in the existing_ids set."""
        if 'fat_id' not in df.columns or not existing_ids:
            # No filtering needed if column missing or no existing IDs to compare against
            return df

        print("DEBUG: Filtering DataFrame for new FAT IDs...")
        df['fat_id_clean_temp'] = df['fat_id'].astype(
            str).str.strip().str.upper()
        filtered_df = df[~df['fat_id_clean_temp'].isin(existing_ids)].copy()
        filtered_df.drop(columns=['fat_id_clean_temp'], inplace=True)
        print(
            f"DEBUG: Filtering complete. Kept {len(filtered_df)} new records.")
        return filtered_df

    def process_uploaded_asset_file(self, uploaded_file) -> Optional[pd.DataFrame]:
        """
        Processes an uploaded asset file (CSV assumed).
        Applies the AssetPipeline, fetches existing FAT IDs, and returns a DataFrame
        containing only the records with new FAT IDs.

        Args:
            uploaded_file: The file object from st.file_uploader.

        Returns:
            A single processed pandas DataFrame, or None if an error occurs.
        """
        try:
            print("DEBUG: Starting file processing...")
            df = pd.read_csv(uploaded_file)
            print(f"DEBUG: CSV loaded successfully. Shape: {df.shape}")

            # --- Run the main processing pipeline ---
            print("DEBUG: Starting asset data processing pipeline...")
            pipeline = AssetPipeline()
            processed_df = pipeline.run(df)
            if processed_df is None:
                # Error logged within pipeline.run()
                st.error("Data processing pipeline failed.")
                return None
            print(
                "DEBUG: Asset data processing pipeline finished. Shape after processing: {processed_df.shape}")

            # --- Fetch existing IDs ---
            db_fat_id_set, fetch_error = self._get_existing_fat_ids()
            if fetch_error:
                st.error(fetch_error)
                return None

            # --- Filter for new records ---
            if 'fat_id' not in processed_df.columns:
                print(
                    "WARN: 'fat_id' column not found after processing. Cannot filter new records.")
                filtered_df = processed_df  # Return all if filtering not possible
            elif not db_fat_id_set:
                print(
                    "DEBUG: No existing FAT IDs in DB. All records are considered new.")
                filtered_df = processed_df  # Return all if DB is empty
            else:
                filtered_df = self._filter_new_records(
                    processed_df, db_fat_id_set)

                if filtered_df.empty:
                    st.info(
                        "All FAT IDs in the uploaded file already exist in the database. No new records to display/insert.")
                else:
                    st.success(
                        f"Found {len(filtered_df)} new FAT ID records in the uploaded file.")

            # Return the final DataFrame (filtered or original)
            return filtered_df

        except pd.errors.ParserError as e:
            print(
                f"ERROR: Failed to parse uploaded file '{uploaded_file.name}'. Error: {e}")
            st.error(f"Failed to parse uploaded file: {e}")
            return None
        except KeyError as e:
            print(
                f"ERROR: Missing expected column during processing. Error: {e}")
            st.error(
                f"Processing error: Missing expected column '{e}'. Please check the file structure.")
            return None
        except Exception as e:
            print(
                f"ERROR: An unexpected error occurred during file processing. Error: {e}")
            st.error(
                f"An unexpected error occurred during file processing: {e}")
            return None

    def insert_asset_dataframe(self, df_processed: pd.DataFrame) -> Tuple[int, int]:
        """
        Splits the processed DataFrame using AssetPipeline and inserts data
        into the respective asset tables, handling potential duplicates via ON CONFLICT.

        Args:
            df_processed: The processed (and potentially user-edited) DataFrame
                          containing combined asset data.

        Returns:
            Tuple (inserted_count, error_count).
        """
        attempted_count = 0  # Tracks rows attempted to insert
        error_count = 0

        if df_processed is None or df_processed.empty:
            st.warning("No processed data provided for insertion.")
            return 0, 0

        # --- Split the data just before insertion using the pipeline ---
        try:
            print("DEBUG: Splitting data before insertion...")
            pipeline = AssetPipeline()
            split_dfs = pipeline.split_data(df_processed.copy())
            if not split_dfs:
                st.error("Failed to split data before insertion. Aborting.")
                return 0, len(df_processed)
        except Exception as split_err:
            st.error(
                f"Error during data splitting before insertion: {split_err}")
            return 0, len(df_processed)
        # -------------------------------------------------------------

        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cur:
                for table_name, df_subset in split_dfs.items():
                    if df_subset.empty:
                        st.info(f"No data to insert into '{table_name}'.")
                        continue

                    st.info(
                        f"Inserting {len(df_subset)} rows into '{table_name}'...")
                    cols_str = ", ".join(
                        [f'"{col}"' for col in df_subset.columns])
                    placeholders = ", ".join(["%s"] * len(df_subset.columns))
                    insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"

                    # --- Conditionally add ON CONFLICT clause ---
                    # Apply ON CONFLICT only to tables where fat_id is expected to be unique
                    # Adjust this set based on your actual database schema constraints
                    # Example: Only user_terminals has unique fat_id
                    tables_with_fat_id_pk = {"user_terminals"}
                    if table_name in tables_with_fat_id_pk:
                        insert_query += " ON CONFLICT (fat_id) DO NOTHING"

                    # Convert DataFrame rows to list of tuples, handling NaT/NaN
                    data_tuples = [
                        tuple(
                            int(x) if isinstance(x, np.integer) else
                            (None if pd.isna(x) else x)
                            for x in row
                        )
                        for row in df_subset.itertuples(index=False, name=None)
                    ]

                    try:
                        cur.executemany(insert_query, data_tuples)
                        attempted_count += len(data_tuples)
                    except Psycopg2Error as insert_err:
                        conn.rollback()  # Rollback this batch
                        st.error(
                            f"Error inserting into '{table_name}': {insert_err}")
                        # Assume all failed in batch
                        error_count += len(data_tuples)
                        continue  # Continue to next table

                # Summary message
                st.success(f"Attempted to process data for all tables.")
                conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            st.error(f"General error during DataFrame insertion: {e}")
        finally:
            if conn:
                self.db_pool.putconn(conn)

        return attempted_count, error_count

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

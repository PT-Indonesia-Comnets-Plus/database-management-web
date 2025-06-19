# core/services/AssetDataService.py

import pandas as pd
import streamlit as st
from psycopg2 import pool, Error as Psycopg2Error, OperationalError, InterfaceError
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from core.services.etl_proces import AssetPipeline
import asyncio
from ..utils.database import get_robust_connection, execute_with_retry, is_connection_alive, cache_query_result, CACHE_CONFIG

# Configure logging
logger = logging.getLogger(__name__)


class AssetDataService:
    """
    Service class for managing asset data interactions with the database.
    Handles loading, inserting, updating, deleting, and processi            ut.kapasitas_olt,
            ut.kapasitas_port_olt,
            ut.olt_port,a                'kapasitas_olt': 'user_terminals',
                'kapasitas_port_olt': 'user_terminals',
                'olt_port': 'user_terminals',t data.
    Enhanced with intelligent caching for better performance.
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

        # Initialize column manager for dynamic columns
        self._column_manager = None
        # Cache for column mapping to avoid repeated database calls
        self._column_mapping_cache = None
        self._column_mapping_cache_time = None
        self._column_mapping_cache_ttl = 300  # 5 minutes cache

        # Cache for table columns to avoid repeated INFORMATION_SCHEMA queries
        self._table_columns_cache = {}
        self._table_columns_cache_time = None
        self._table_columns_cache_ttl = 600  # 10 minutes cache

        # Cache for comprehensive query to avoid rebuilding
        self._comprehensive_query_cache = None
        self._comprehensive_query_cache_time = None
        self._comprehensive_query_cache_ttl = 600  # 10 minutes cache

    @property
    def column_manager(self):
        """Lazy initialization of column manager."""
        if self._column_manager is None:
            # Import here to avoid circular imports
            from features.home.views.add_column import ColumnManager
            self._column_manager = ColumnManager(self.db_pool)
        return self._column_manager

    def get_column_mapping(self, force_refresh: bool = False) -> dict:
        """
        Get column mapping with caching to improve performance.

        Args:
            force_refresh: If True, bypass cache and reload from database

        Returns:
            Dictionary mapping database column names to display names
        """
        import time

        current_time = time.time()

        # Check if cache is valid
        if (not force_refresh and
            self._column_mapping_cache is not None and
            self._column_mapping_cache_time is not None and
                (current_time - self._column_mapping_cache_time) < self._column_mapping_cache_ttl):
            logger.debug("Using cached column mapping")
            return self._column_mapping_cache

        # Load fresh mapping
        try:
            from features.home.views.search import get_complete_column_mapping
            mapping = get_complete_column_mapping(self)

            # Update cache
            self._column_mapping_cache = mapping
            self._column_mapping_cache_time = current_time

            logger.info(
                f"Refreshed column mapping cache with {len(mapping)} columns")
            return mapping

        except Exception as e:
            logger.error(f"Error loading column mapping: {e}")
            # Return cached version if available, even if expired
            if self._column_mapping_cache is not None:
                logger.warning("Using expired cache due to error")
                return self._column_mapping_cache
            # Return minimal fallback
            return {
                'fat_id': 'FATID',
                'olt': 'OLT',
                'fdt_id': 'FDT ID'
            }

    def invalidate_column_mapping_cache(self):
        """Invalidate the column mapping cache. Call this when columns are added/removed."""
        self._column_mapping_cache = None
        self._column_mapping_cache_time = None
        logger.info("Column mapping cache invalidated")

    def invalidate_comprehensive_query_cache(self):
        """Invalidate the comprehensive query cache. Call this when table schema changes."""
        self._comprehensive_query_cache = None
        self._comprehensive_query_cache_time = None
        logger.info("Comprehensive query cache invalidated")

    def invalidate_table_columns_cache(self):
        """Invalidate the table columns cache. Call this when table schema changes."""
        self._table_columns_cache = {}
        self._table_columns_cache_time = None
        logger.info("Table columns cache invalidated")

    def invalidate_all_cache(self):
        """Invalidate all caches. Call this when significant schema changes occur."""
        self.invalidate_column_mapping_cache()
        self.invalidate_comprehensive_query_cache()
        self.invalidate_table_columns_cache()
        logger.info("All caches invalidated")

    def _execute_query(self, query: str, params: Optional[tuple] = None, fetch: str = "all") -> Tuple[Optional[List[Tuple]], Optional[List[str]], Optional[str]]:
        """
        Executes a SQL query using the connection pool with robust error handling.

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
        def _execute_operation(conn):
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
                    return [], [], None  # Success, no error message
                else:
                    conn.commit()
                    return [], [], None  # Success, no error message

        try:
            return execute_with_retry(self.db_pool, _execute_operation, max_retries=3)
        except (OperationalError, InterfaceError) as e:
            return None, None, f"Database Connection Error: {e}"
        except Psycopg2Error as db_err:
            return None, None, f"Database Error: {db_err}"
        except Exception as e:
            return None, None, f"Execution Error: {e}"

    @cache_query_result(ttl_seconds=CACHE_CONFIG['asset_data_ttl'])
    def load_all_assets(self, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Loads essential asset data for the dashboard by joining relevant tables.
        Results are cached for improved performance.

        Args:
            limit: Maximum number of rows to load. If None, loads all.

        Returns:
            A pandas DataFrame containing the essential asset data, or None if an error occurs.
        """
        logger.info(f"Loading asset data from database (limit: {limit})")

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

        df = pd.DataFrame(data, columns=columns)
        logger.info(f"Loaded {len(df)} asset records")
        return df

    @cache_query_result(ttl_seconds=CACHE_CONFIG['aggregation_ttl'])
    def get_asset_aggregations(self, group_by_column: str) -> Optional[pd.DataFrame]:
        """
        Get aggregated asset data for improved dashboard performance.
        Results are cached for fast repeated access.

        Args:
            group_by_column: Column to group by (e.g., 'kota_kab', 'brand_olt')

        Returns:
            DataFrame with aggregated data
        """
        allowed_columns = ['kota_kab', 'brand_olt',
                           'fat_filter_pemakaian', 'olt']
        if group_by_column not in allowed_columns:
            st.error(f"Invalid group by column: {group_by_column}")
            return None

        query = f"""
            SELECT 
                cl.{group_by_column},
                COUNT(DISTINCT ut.fat_id) as total_assets,
                COUNT(DISTINCT ut.olt) as total_olt,
                COUNT(DISTINCT ut.fdt_id) as total_fdt,
                COALESCE(SUM(hc.total_hc), 0) as total_hc,
                COALESCE(AVG(hc.total_hc), 0) as avg_hc
            FROM user_terminals ut
            LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
            LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
            WHERE cl.{group_by_column} IS NOT NULL
            GROUP BY cl.{group_by_column}
            ORDER BY total_hc DESC
        """

        data, columns, error = self._execute_query(query, fetch="all")

        if error:
            st.error(f"Failed to load aggregations: {error}")
            return None

        if data is None:
            return pd.DataFrame(columns=columns or [])

        return pd.DataFrame(data, columns=columns)    @ cache_query_result(ttl_seconds=CACHE_CONFIG['map_data_ttl'])

    def get_map_data(self, kota_filter: Optional[str] = None, limit: Optional[int] = 1000) -> Optional[pd.DataFrame]:
        """
        Get optimized data specifically for map rendering with caching.

        Args:
            kota_filter: Filter by specific city/regency
            limit: Maximum number of points to return (None for unlimited)

        Returns:
            DataFrame optimized for map visualization
        """
        base_query = """
            SELECT 
                ut.fat_id,
                ut.latitude_fat,
                ut.longitude_fat,
                ut.olt,
                cl.kota_kab,
                COALESCE(hc.total_hc, 0) as total_hc
            FROM user_terminals ut
            LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
            LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
            WHERE ut.latitude_fat IS NOT NULL 
            AND ut.longitude_fat IS NOT NULL
            AND ut.latitude_fat BETWEEN -11 AND 6
            AND ut.longitude_fat BETWEEN 95 AND 141        """

        params = []
        if kota_filter and kota_filter != 'All':
            base_query += " AND cl.kota_kab = %s"
            params.append(kota_filter)

        base_query += " ORDER BY hc.total_hc DESC NULLS LAST"

        if limit is not None:
            base_query += " LIMIT %s"
            params.append(limit)

        data, columns, error = self._execute_query(
            base_query, tuple(params) if params else None, fetch="all")

        if error:
            st.error(f"Failed to load map data: {error}")
            return None

        if data is None:
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
            return 0, 0        # --- Split the data just before insertion using the pipeline ---
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

        def _perform_insertion(conn):
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
                        nonlocal attempted_count
                        attempted_count += len(data_tuples)
                    except Psycopg2Error as insert_err:
                        conn.rollback()  # Rollback this batch
                        st.error(
                            f"Error inserting into '{table_name}': {insert_err}")
                        # Assume all failed in batch
                        nonlocal error_count
                        error_count += len(data_tuples)
                        continue  # Continue to next table

                # Summary message
                st.success(f"Attempted to process data for all tables.")
                conn.commit()
                return attempted_count, error_count

        try:
            return execute_with_retry(self.db_pool, _perform_insertion, max_retries=3)
        except (OperationalError, InterfaceError) as e:
            st.error(f"Database connection error during insertion: {e}")
            return 0, len(df_processed)
        except Exception as e:
            st.error(f"General error during DataFrame insertion: {e}")
            return 0, len(df_processed)

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

    def update_asset_table(self, table_name: str, identifier_col: str, identifier_value: Any, update_data: Dict[str, Any]) -> Optional[str]:
        """
        Updates a record in any specified table.

        Args:
            table_name: The name of the table to update.
            identifier_col: The column name to identify the record.
            identifier_value: The value of the identifier column.
            update_data: Dictionary of columns and their new values.

        Returns:
            Error message string if failed, None if successful.
        """
        if not update_data:
            return "No update data provided."

        # Validate table name for security
        allowed_tables = ["user_terminals", "clusters", "home_connecteds",
                          "dokumentasis", "additional_informations", "pelanggans"]
        if table_name not in allowed_tables:
            return f"Table '{table_name}' is not allowed for updates."

        # Convert display column names to database column names
        db_update_data = self._convert_display_to_db_columns(
            table_name, update_data)

        db_identifier_col = identifier_col.lower()
        set_clause = ", ".join(
            [f'"{col}" = %s' for col in db_update_data.keys()])
        values = list(db_update_data.values()) + [identifier_value]
        query = f'UPDATE {table_name} SET {set_clause} WHERE "{db_identifier_col}" = %s'

        _, _, error = self._execute_query(query, tuple(values), fetch="none")

        if error:
            st.error(f"Failed to update {table_name}: {error}")
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

    def delete_asset_table(self, table_name: str, identifier_col: str, identifier_value: Any) -> Optional[str]:
        """
        Deletes a record from any specified table.

        Args:
            table_name: The name of the table to delete from.
            identifier_col: The column name to identify the record.
            identifier_value: The value of the identifier column.

        Returns:
            Error message string if failed, None if successful.
        """
        # Validate table name for security
        allowed_tables = ["user_terminals", "clusters", "home_connecteds",
                          "dokumentasis", "additional_informations", "pelanggans"]
        if table_name not in allowed_tables:
            return f"Table '{table_name}' is not allowed for deletion."

        db_identifier_col = identifier_col.lower()
        query = f'DELETE FROM {table_name} WHERE "{db_identifier_col}" = %s'

        _, _, error = self._execute_query(
            query, (identifier_value,), fetch="none")

        if error:
            st.error(f"Failed to delete from {table_name}: {error}")
            return f"Deletion Error: {error}"
        return None  # Success

    def search_table(self, table_name: str, column_name: str, value: Any) -> Optional[pd.DataFrame]:
        """
        Search for records in any specified table.

        Args:
            table_name: The name of the table to search in.
            column_name: The name of the column to search.
            value: The value to search for.

        Returns:
            A pandas DataFrame containing the matching records, or None if an error occurs.
        """
        # Validate table name for security
        allowed_tables = ["user_terminals", "clusters", "home_connecteds",
                          "dokumentasis", "additional_informations", "pelanggans"]
        if table_name not in allowed_tables:
            st.error(f"Table '{table_name}' is not allowed for search.")
            return None

        db_column_name = column_name.lower()
        query = f'SELECT * FROM {table_name} WHERE "{db_column_name}" ILIKE %s'

        data, columns, error = self._execute_query(
            query, (f"%{value}%",), fetch="all")

        if error:
            st.error(f"Failed to search {table_name}: {error}")
            return None
        if data is None:
            st.warning(f"No data returned from {table_name} search query.")
            return pd.DataFrame(columns=columns or [])
        return pd.DataFrame(data, columns=columns)

    def load_comprehensive_asset_data(self, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Load comprehensive asset data from all tables with complete joins.        This method provides all available data for comprehensive search and detail views.

        Args:
            limit: Maximum number of rows to load. If None, loads all.

        Returns:
            DataFrame with comprehensive asset data from all tables
        """
        logger.info(f"Loading comprehensive asset data (limit: {limit})")

        # Build dynamic query that includes all columns from all tables, handling duplicates
        query = self._build_comprehensive_query()

        query_params = []
        if limit is not None:
            query += " LIMIT %s"
            query_params.append(limit)
        query += ";"

        data, columns, error = self._execute_query(
            query, tuple(query_params) if query_params else None, fetch="all")

        if error:
            logger.error(f"Failed to load comprehensive asset data: {error}")
            return None
        if data is None:
            logger.warning("No comprehensive asset data returned from query")
            return pd.DataFrame(columns=columns or [])

        df = pd.DataFrame(data, columns=columns)
        logger.info(
            f"Loaded {len(df)} comprehensive asset records with {len(columns)} columns")
        logger.info(f"Raw database columns: {columns}")

        return df

    def update_asset_comprehensive(self, pk_column: str, pk_value: Any, update_data: Dict[str, Any]) -> Optional[str]:
        """
        Update asset data across multiple tables based on the field being updated.
        Automatically determines which table to update based on the field name.
        Since dynamic columns are now added physically to tables, this handles them transparently.

        Args:
            pk_column: Primary key column name (e.g., 'fat_id', 'olt', 'fdt_id')
            pk_value: Primary key value
            update_data: Dictionary of field names and their new values

        Returns:
            Error message if failed, None if successful
        """
        if not update_data:
            return "No data provided for update"

        try:
            # Field mapping to determine which table to update
            field_to_table_mapping = {
                # User Terminals fields (includes dynamic columns now)
                'fat_id': 'user_terminals',
                'hostname_olt': 'user_terminals',
                'latitude_olt': 'user_terminals',
                'longitude_olt': 'user_terminals',
                'brand_olt': 'user_terminals',
                'type_olt': 'user_terminals',
                'kapasitas_olt': 'user_terminals',
                'kapasitas_port_olt': 'user_terminals',
                'olt_port': 'user_terminals',
                'olt': 'user_terminals',
                'interface_olt': 'user_terminals',
                'fdt_id': 'user_terminals',
                'status_osp_amarta_fdt': 'user_terminals',
                'jumlah_splitter_fdt': 'user_terminals',
                'kapasitas_splitter_fdt': 'user_terminals',
                'fdt_new_existing': 'user_terminals',
                'port_fdt': 'user_terminals',
                'latitude_fdt': 'user_terminals',
                'longitude_fdt': 'user_terminals',
                'jumlah_splitter_fat': 'user_terminals',
                'kapasitas_splitter_fat': 'user_terminals',
                'latitude_fat': 'user_terminals',
                'longitude_fat': 'user_terminals',
                'status_osp_amarta_fat': 'user_terminals',
                'fat_kondisi': 'user_terminals',
                'fat_filter_pemakaian': 'user_terminals',
                'keterangan_full': 'user_terminals',
                'fat_id_x': 'user_terminals',
                'filter_fat_cap': 'user_terminals',                # Clusters fields
                'latitude_cluster': 'clusters',
                'longitude_cluster': 'clusters',
                'area_kp': 'clusters',
                'kota_kab': 'clusters',
                'kecamatan': 'clusters',
                'kelurahan': 'clusters',
                'up3': 'clusters',
                'ulp': 'clusters',

                # Display name mappings for clusters
                'Latitude Cluster': 'clusters',
                'Longitude Cluster': 'clusters',
                'Area Kp': 'clusters',
                'Kota/Kab': 'clusters',
                'Kecamatan': 'clusters',
                'Kelurahan': 'clusters',
                'UP3': 'clusters',
                'ULP': 'clusters',

                # Home Connected fields
                'hc_old': 'home_connecteds',
                'hc_icrm': 'home_connecteds',
                'total_hc': 'home_connecteds',
                'cleansing_hp': 'home_connecteds',

                # Display name mappings for home_connecteds
                'HC Old': 'home_connecteds',
                'HC ICRM': 'home_connecteds',
                'Total HC': 'home_connecteds',
                'Cleansing HP': 'home_connecteds',

                # Dokumentasi fields
                'dokumentasi_status_osp_amarta_fat': 'dokumentasis',
                'link_dokumen_feeder': 'dokumentasis',
                'keterangan_dokumen': 'dokumentasis',
                'link_data_aset': 'dokumentasis',
                'keterangan_data_aset': 'dokumentasis',
                'link_maps': 'dokumentasis',
                'update_aset': 'dokumentasis',
                'amarta_update': 'dokumentasis',

                # Display name mappings for dokumentasis
                'Dokumentasi Status Osp Amarta Fat': 'dokumentasis',
                'Link Dokumen Feeder': 'dokumentasis',
                'Keterangan Dokumen': 'dokumentasis',
                'Link Data Aset': 'dokumentasis',
                'Keterangan Data Aset': 'dokumentasis',
                'Link Maps': 'dokumentasis',
                'Update Aset': 'dokumentasis',
                'Amarta Update': 'dokumentasis',  # Additional Information fields
                'pa': 'additional_informations',
                'tanggal_rfs': 'additional_informations',
                'mitra': 'additional_informations',
                'kategori': 'additional_informations',
                'sumber_datek': 'additional_informations',

                # Display name mappings for additional_informations
                'PA': 'additional_informations',
                'Tanggal RFS': 'additional_informations',
                'Tanggal Rfs': 'additional_informations',
                'Mitra': 'additional_informations',
                'Kategori': 'additional_informations',
                'Sumber Datek': 'additional_informations',
            }

            # Get dynamic columns to add them to the mapping
            try:
                dynamic_columns = self.column_manager.get_dynamic_columns(
                    'user_terminals', active_only=True)
                for col in dynamic_columns:
                    # Dynamic columns are physically in user_terminals table
                    field_to_table_mapping[col['display_name']
                                           ] = 'user_terminals'
                    field_to_table_mapping[col['column_name']
                                           ] = 'user_terminals'
            except Exception as e:
                logger.warning(
                    f"Could not load dynamic columns for mapping: {e}")

            # Group updates by table
            updates_by_table = {}

            for field_name, new_value in update_data.items():
                table_name = field_to_table_mapping.get(
                    field_name, 'user_terminals')  # Default to user_terminals

                if table_name not in updates_by_table:
                    updates_by_table[table_name] = {}

                updates_by_table[table_name][field_name] = new_value

            # Execute updates for each table
            pk_col_db = pk_column.lower()

            for table_name, table_updates in updates_by_table.items():
                error = self.update_asset_table(
                    table_name, pk_col_db, pk_value, table_updates)
                if error:
                    return error

            logger.info(
                f"Successfully updated {len(update_data)} fields across {len(updates_by_table)} tables for {pk_column}={pk_value}")
            return None  # Success

        except Exception as e:
            error_msg = f"Error in comprehensive update: {e}"
            logger.error(error_msg)
            return error_msg

    def build_comprehensive_query(self) -> str:
        """
        Public method to build comprehensive query for external use.
        This method is used by search helpers and other services that need
        to build dynamic queries with all columns from all tables.

        Returns:
            SQL query string
        """
        return self._build_comprehensive_query()

    def _build_comprehensive_query(self) -> str:
        """
        Build a comprehensive query that dynamically includes all columns from all tables,
        handling duplicate column names with prefixes.

        Returns:
            SQL query string
        """
        try:
            # Get column information for each table
            tables_info = {
                'ut': 'user_terminals',
                'cl': 'clusters',
                'hc': 'home_connecteds',
                'dk': 'dokumentasis',
                'ai': 'additional_informations'
            }

            # Build SELECT clause with all columns
            select_parts = []

            # Always include all columns from user_terminals (main table) without prefix
            # For other tables, get their columns and add with prefixes to avoid conflicts
            select_parts.append("ut.*")
            # Skip 'ut'
            for alias, table_name in list(tables_info.items())[1:]:
                table_columns = self._get_table_columns(table_name)
                for col in table_columns:
                    if col in ['fat_id', 'id']:
                        # Skip fat_id and id from other tables to avoid redundancy
                        # fat_id: Only use from main table (user_terminals)
                        # id: Internal primary keys not needed in display
                        continue
                    elif col in ['created_at', 'updated_at']:
                        # Add prefix to timestamp columns to avoid conflicts
                        select_parts.append(f"{alias}.{col} as {alias}_{col}")
                    elif col == 'status_osp_amarta_fat' and alias == 'dk':
                        # Special case for dokumentasis
                        select_parts.append(
                            f"{alias}.{col} as dokumentasi_{col}")
                    else:
                        # Use original column name for other columns
                        select_parts.append(f"{alias}.{col}")

            query = f"""
            SELECT {', '.join(select_parts)}
            FROM user_terminals ut
            LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
            LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
            LEFT JOIN dokumentasis dk ON ut.fat_id = dk.fat_id
            LEFT JOIN additional_informations ai ON ut.fat_id = ai.fat_id
            ORDER BY ut.fat_id
            """

            return query

        except Exception as e:
            logger.warning(
                f"Error building dynamic query, falling back to basic query: {e}")
            # Fallback to basic query if dynamic building fails
            return """
            SELECT ut.*, 
                   cl.latitude_cluster, cl.longitude_cluster, cl.area_kp, cl.kota_kab,
                   cl.kecamatan, cl.kelurahan, cl.up3, cl.ulp,
                   hc.hc_old, hc.hc_icrm, hc.total_hc, hc.cleansing_hp,                   dk.status_osp_amarta_fat as dokumentasi_status_osp_amarta_fat,
                   dk.link_dokumen_feeder, dk.keterangan_dokumen, dk.link_data_aset,
                   dk.keterangan_data_aset, dk.link_maps, dk.update_aset, dk.amarta_update,
                   ai.pa, ai.tanggal_rfs, ai.mitra, ai.kategori, ai.sumber_datek
            FROM user_terminals ut
            LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
            LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
            LEFT JOIN dokumentasis dk ON ut.fat_id = dk.fat_id
            LEFT JOIN additional_informations ai ON ut.fat_id = ai.fat_id
            ORDER BY ut.fat_id
            """

    def _get_table_columns(self, table_name: str) -> List[str]:
        """
        Get all column names for a specific table with caching.

        Args:
            table_name: Name of the table

        Returns:
            List of column names
        """
        import time

        current_time = time.time()

        # Check if cache is valid
        if (self._table_columns_cache_time and
            current_time - self._table_columns_cache_time < self._table_columns_cache_ttl and
                table_name in self._table_columns_cache):
            return self._table_columns_cache[table_name]

        try:
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position
            """

            data, columns, error = self._execute_query(query, (table_name,))
            if error or not data:
                logger.warning(
                    f"Could not get columns for table {table_name}: {error}")
                return []

            column_list = [row[0] for row in data]

            # Update cache
            if not self._table_columns_cache_time:
                self._table_columns_cache_time = current_time
            self._table_columns_cache[table_name] = column_list

            return column_list

        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            return []

    def _convert_display_to_db_columns(self, table_name: str, display_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert display column names back to database column names.

        Args:
            table_name: Target table name
            display_data: Data with display column names

        Returns:
            Data with database column names
        """
        # Create reverse mapping from display name to database name
        display_to_db_mapping = {
            # User terminals mappings
            'FATID': 'fat_id',
            'Hostname Olt': 'hostname_olt',
            'Latitude Olt': 'latitude_olt',
            'Longitude Olt': 'longitude_olt',
            'Brand Olt': 'brand_olt',
            'Type Olt': 'type_olt',
            'Kapasitas Olt': 'kapasitas_olt',
            'Kapasitas Port Olt': 'kapasitas_port_olt',
            'Olt Port': 'olt_port',
            'OLT': 'olt',
            'Interface Olt': 'interface_olt',
            'FDT ID': 'fdt_id',
            'Status Osp Amarta Fdt': 'status_osp_amarta_fdt',
            'Jumlah Splitter Fdt': 'jumlah_splitter_fdt',
            'Kapasitas Splitter Fdt': 'kapasitas_splitter_fdt',
            'Fdt New Existing': 'fdt_new_existing',
            'Port Fdt': 'port_fdt',
            'Latitude Fdt': 'latitude_fdt',
            'Longitude Fdt': 'longitude_fdt',
            'Jumlah Splitter Fat': 'jumlah_splitter_fat',
            'Kapasitas Splitter Fat': 'kapasitas_splitter_fat',
            'Latitude Fat': 'latitude_fat',
            'Longitude Fat': 'longitude_fat',
            'Status OSP AMARTA FAT': 'status_osp_amarta_fat',
            'Fat Kondisi': 'fat_kondisi',
            'Fat Filter Pemakaian': 'fat_filter_pemakaian',
            'Keterangan Full': 'keterangan_full',
            'FAT ID X': 'fat_id_x',
            'Filter Fat Cap': 'filter_fat_cap',

            # Clusters mappings
            'Latitude Cluster': 'latitude_cluster',
            'Longitude Cluster': 'longitude_cluster',
            'Area Kp': 'area_kp',
            'Kota/Kab': 'kota_kab',
            'Kecamatan': 'kecamatan',
            'Kelurahan': 'kelurahan',
            'UP3': 'up3',
            'ULP': 'ulp',

            # Home connecteds mappings
            'HC Old': 'hc_old',
            'HC ICRM': 'hc_icrm',
            'Total HC': 'total_hc',
            'Cleansing HP': 'cleansing_hp',

            # Dokumentasis mappings
            'Dokumentasi Status Osp Amarta Fat': 'status_osp_amarta_fat',
            'Link Dokumen Feeder': 'link_dokumen_feeder',
            'Keterangan Dokumen': 'keterangan_dokumen',
            'Link Data Aset': 'link_data_aset',
            'Keterangan Data Aset': 'keterangan_data_aset',
            'Link Maps': 'link_maps',
            'Update Aset': 'update_aset',
            'Amarta Update': 'amarta_update',

            # Additional informations mappings
            'PA': 'pa',
            'Tanggal RFS': 'tanggal_rfs',
            'Tanggal Rfs': 'tanggal_rfs',
            'Mitra': 'mitra',
            'Kategori': 'kategori',
            'Sumber Datek': 'sumber_datek',
        }

        converted_data = {}
        for display_name, value in display_data.items():
            # Try to find database column name
            db_column = display_to_db_mapping.get(display_name)
            if db_column:
                converted_data[db_column] = value
            else:
                # If no mapping found, assume it's already a database column name
                # or try to convert using simple rule (title case to snake_case)
                db_column = display_name.lower().replace(' ', '_')
                converted_data[db_column] = value

        return converted_data

    # ...existing code...

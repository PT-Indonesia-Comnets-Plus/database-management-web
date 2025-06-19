# dynamic_search_helper.py
"""
Helper untuk memperbaiki dan mengoptimalkan sistem search secara holistik.
Menyediakan unified search interface yang menggabungkan static dan dynamic columns.
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from core.services.AssetDataService import AssetDataService

logger = logging.getLogger(__name__)


class UnifiedSearchService:
    """
    Service untuk mengelola pencarian holistik yang menggabungkan:
    1. Static columns dari database utama
    2. Dynamic columns dari system kolom dinamis
    3. Search dengan multiple filters
    4. Fuzzy search dan exact match
    """

    def __init__(self, asset_data_service: AssetDataService):
        self.asset_data_service = asset_data_service
        self._column_cache = {}
        self._search_cache = {}
        # Cache for search queries to avoid rebuilding every time
        self._query_cache = {}
        self._query_cache_ttl = 300  # 5 minutes

    def get_all_searchable_columns(self, table_name: str = 'user_terminals') -> Dict[str, Dict]:
        """
        Ambil semua kolom yang bisa dicari (static + dynamic).

        Returns:
            Dict dengan format: {display_name: {type: 'static'|'dynamic', metadata: {...}}}
        """
        if table_name in self._column_cache:
            return self._column_cache[table_name]

        searchable_columns = {}

        # 1. Static columns (predefined)
        static_columns = {
            'FATID': {
                'type': 'static',
                'db_column': 'fat_id',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'core'
            },
            'OLT': {
                'type': 'static',
                'db_column': 'olt',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'core'
            },
            'FDT ID': {
                'type': 'static',
                'db_column': 'fdt_id',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'core'
            },
            'Hostname OLT': {
                'type': 'static',
                'db_column': 'hostname_olt',
                'table': 'user_terminals',
                'search_type': 'partial',
                'category': 'olt'
            },
            'Brand OLT': {
                'type': 'static',
                'db_column': 'brand_olt',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'olt'
            },
            'Type OLT': {
                'type': 'static',
                'db_column': 'type_olt',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'olt'
            },
            'Kota/Kab': {
                'type': 'static',
                'db_column': 'kota_kab',
                'table': 'clusters',
                'search_type': 'exact_and_partial',
                'category': 'location'
            },
            'Kecamatan': {
                'type': 'static',
                'db_column': 'kecamatan',
                'table': 'clusters',
                'search_type': 'exact_and_partial',
                'category': 'location'
            },
            'Kelurahan': {
                'type': 'static',
                'db_column': 'kelurahan',
                'table': 'clusters',
                'search_type': 'exact_and_partial',
                'category': 'location'
            },
            'FAT KONDISI': {
                'type': 'static',
                'db_column': 'fat_kondisi',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'status'
            },
            'Status OSP AMARTA FAT': {
                'type': 'static',
                'db_column': 'status_osp_amarta_fat',
                'table': 'user_terminals',
                'search_type': 'exact_and_partial',
                'category': 'status'
            }
        }

        searchable_columns.update(static_columns)

        # 2. Dynamic columns
        try:
            dynamic_columns = self.asset_data_service.column_manager.get_dynamic_columns(
                table_name, active_only=True)

            for col in dynamic_columns:
                if col.get('is_searchable', False):
                    searchable_columns[col['display_name']] = {
                        'type': 'dynamic',
                        'column_id': col['id'],
                        'db_column': col['column_name'],
                        'data_type': col['column_type'],
                        'search_type': 'exact_and_partial',
                        'category': 'dynamic'
                    }
        except Exception as e:
            logger.warning(f"Could not load dynamic columns: {e}")

        self._column_cache[table_name] = searchable_columns
        return searchable_columns

    def search_unified(self, search_params: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Pencarian holistik yang menggabungkan multiple search methods.

        Args:
            search_params: {
                'primary_column': str,     # Kolom utama untuk pencarian
                'primary_value': str,      # Nilai utama untuk pencarian
                'additional_filters': Dict[str, str],  # Filter tambahan
                'search_mode': str,        # 'exact', 'partial', 'auto'
                'limit': int               # Limit hasil
            }

        Returns:
            DataFrame dengan hasil pencarian
        """
        try:
            primary_column = search_params.get('primary_column')
            primary_value = search_params.get('primary_value')
            additional_filters = search_params.get('additional_filters', {})
            search_mode = search_params.get('search_mode', 'auto')
            limit = search_params.get('limit', 1000)

            if not primary_column or not primary_value:
                logger.error("Primary column and value are required")
                return pd.DataFrame()

            # Get column metadata
            searchable_columns = self.get_all_searchable_columns()
            if primary_column not in searchable_columns:
                logger.error(f"Column '{primary_column}' is not searchable")
                return pd.DataFrame()

            column_meta = searchable_columns[primary_column]

            # Execute primary search
            if column_meta['type'] == 'static':
                result_df = self._search_static_column(
                    column_meta, primary_value, search_mode, limit)
            else:
                result_df = self._search_dynamic_column(
                    column_meta, primary_value, search_mode, limit)

            if result_df is None or result_df.empty:
                return pd.DataFrame()            # Apply additional filters
            if additional_filters:
                result_df = self._apply_additional_filters(
                    result_df, additional_filters, searchable_columns)

            # Enrich with dynamic columns data for all results
            result_df = self._enrich_with_dynamic_columns(result_df)

            logger.info(f"Unified search returned {len(result_df)} results")
            return result_df

        except Exception as e:
            logger.error(f"Error in unified search: {e}")
            return pd.DataFrame()

    def _search_static_column(self, column_meta: Dict, value: str,
                              search_mode: str, limit: int) -> Optional[pd.DataFrame]:
        """Search dalam static column menggunakan optimized query."""
        try:
            db_column = column_meta['db_column']
            table = column_meta.get('table', 'user_terminals')
            # Determine search operator and add table alias
            if search_mode == 'exact':
                where_condition = f"ut.{db_column} = %s"
                params = [value]
            elif search_mode == 'partial':
                where_condition = f"LOWER(ut.{db_column}) LIKE LOWER(%s)"
                params = [f"%{value}%"]
            else:  # auto mode
                # Try exact first, then partial if no results
                exact_result = self._search_static_column(
                    column_meta, value, 'exact', limit)
                if exact_result is not None and not exact_result.empty:
                    return exact_result
                return self._search_static_column(
                    column_meta, value, 'partial', limit)            # Use database filtering for efficiency (not Python filtering)
            # Create optimized comprehensive query with WHERE clause

            if table == 'user_terminals':
                # Build efficient query with database-level filtering
                if search_mode == 'exact':
                    where_condition = f"ut.{db_column} = %s"
                    params = [value]
                elif search_mode == 'partial':
                    where_condition = f"LOWER(ut.{db_column}) LIKE LOWER(%s)"
                    params = [f"%{value}%"]

                # Use the same comprehensive SELECT from AssetDataService but with filtering
                # This ensures ALL columns including dynamic ones are included from ALL tables
                base_query = self.asset_data_service.build_comprehensive_query()
                # Remove the ORDER BY and add WHERE condition
                base_query_parts = base_query.strip().split('ORDER BY')
                select_and_joins = base_query_parts[0].strip()

                query = select_and_joins + f"""
                    WHERE {where_condition}
                    ORDER BY ut.fat_id
                    LIMIT %s
                """
                params.append(limit if limit else 1000)

                data, columns, error = self.asset_data_service._execute_query(
                    query, tuple(params))

                if error:
                    logger.error(
                        f"Error in optimized comprehensive search: {error}")
                    return None

                if not data:
                    return pd.DataFrame()

                result_df = pd.DataFrame(data, columns=columns)
                logger.info(
                    f"Optimized search returned {len(result_df)} rows with {len(result_df.columns)} columns")
                return result_df

            else:
                # For searches in other tables, use optimized database query too
                # Determine the correct table alias and column
                if table == 'clusters':
                    table_column = f"cl.{db_column}"
                elif table == 'home_connecteds':
                    table_column = f"hc.{db_column}"
                elif table == 'additional_informations':
                    table_column = f"ai.{db_column}"
                elif table == 'dokumentasis':
                    table_column = f"dk.{db_column}"
                else:
                    # fallback to user_terminals
                    table_column = f"ut.{db_column}"

                # Build where condition
                if search_mode == 'exact':
                    where_condition = f"{table_column} = %s"
                    params = [value]
                elif search_mode == 'partial':
                    where_condition = f"LOWER({table_column}) LIKE LOWER(%s)"
                    params = [f"%{value}%"]

                # Same comprehensive query but with different WHERE condition
                base_query = self.asset_data_service.build_comprehensive_query()
                # Remove the ORDER BY and add WHERE condition
                base_query_parts = base_query.strip().split('ORDER BY')
                select_and_joins = base_query_parts[0].strip()

                query = select_and_joins + f"""
                    WHERE {where_condition}
                    ORDER BY ut.fat_id
                    LIMIT %s
                """
                params.append(limit if limit else 1000)

                data, columns, error = self.asset_data_service._execute_query(
                    query, tuple(params))

                if error:
                    logger.error(
                        f"Error in optimized search for {table}: {error}")
                    return None

                if not data:
                    return pd.DataFrame()

                result_df = pd.DataFrame(data, columns=columns)
                logger.info(
                    f"Optimized search in {table} returned {len(result_df)} rows with {len(result_df.columns)} columns")
                return result_df

        except Exception as e:
            logger.error(f"Exception in static column search: {e}")
            return None

    def _search_dynamic_column(self, column_meta: Dict, value: str,
                               search_mode: str, limit: int) -> Optional[pd.DataFrame]:
        """Search dalam dynamic column."""
        try:
            column_id = column_meta['column_id']

            # Determine search pattern
            if search_mode == 'exact':
                search_pattern = value
                like_operator = "="
            elif search_mode == 'partial':
                search_pattern = f"%{value}%"
                like_operator = "LIKE"
            else:  # auto mode
                # Try exact first
                exact_result = self._search_dynamic_column(
                    column_meta, value, 'exact', limit)
                if exact_result is not None and not exact_result.empty:
                    return exact_result
                return self._search_dynamic_column(
                    column_meta, value, 'partial', limit)

            query = """
                SELECT ut.*, cl.kota_kab, cl.kecamatan, cl.kelurahan,
                       hc.total_hc, ai.tanggal_rfs,
                       dcd.column_value as dynamic_value
                FROM user_terminals ut
                LEFT JOIN clusters cl ON ut.fat_id = cl.fat_id
                LEFT JOIN home_connecteds hc ON ut.fat_id = hc.fat_id
                LEFT JOIN additional_informations ai ON ut.fat_id = ai.fat_id
                JOIN dynamic_column_data dcd ON ut.fat_id = dcd.record_id
                WHERE dcd.column_id = %s 
                AND LOWER(dcd.column_value) {} LOWER(%s)
                ORDER BY ut.fat_id
                LIMIT %s
            """.format(like_operator)

            data, columns, error = self.asset_data_service._execute_query(
                query, (column_id, search_pattern, limit))

            if error:
                logger.error(f"Error in dynamic column search: {error}")
                return None

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data, columns=columns)
            # Remove helper column
            if 'dynamic_value' in df.columns:
                df = df.drop('dynamic_value', axis=1)

            return df

        except Exception as e:
            logger.error(f"Exception in dynamic column search: {e}")
            return None

    def _apply_additional_filters(self, df: pd.DataFrame, filters: Dict[str, str],
                                  searchable_columns: Dict) -> pd.DataFrame:
        """Apply additional filters to search results."""
        try:
            filtered_df = df.copy()

            for filter_column, filter_value in filters.items():
                if not filter_value.strip():
                    continue

                # Map display name to actual column name in DataFrame
                actual_column = None

                # Check if it's a direct column match
                if filter_column in filtered_df.columns:
                    actual_column = filter_column
                elif filter_column in searchable_columns:
                    # Map from searchable columns
                    meta = searchable_columns[filter_column]
                    if meta['type'] == 'static':
                        db_col = meta['db_column']
                        # Try common column mappings
                        column_mapping = {
                            'kota_kab': 'kota_kab',
                            'kecamatan': 'kecamatan',
                            'kelurahan': 'kelurahan',
                            'fat_id': 'fat_id',
                            'olt': 'olt',
                            'brand_olt': 'brand_olt',
                            'hostname_olt': 'hostname_olt'
                        }
                        actual_column = column_mapping.get(db_col, db_col)

                if actual_column and actual_column in filtered_df.columns:
                    # Apply case-insensitive partial match
                    mask = filtered_df[actual_column].astype(str).str.lower().str.contains(
                        filter_value.lower(), na=False)
                    filtered_df = filtered_df[mask]
                    logger.info(
                        f"Applied filter {filter_column}={filter_value}, {len(filtered_df)} results remain")

            return filtered_df

        except Exception as e:
            logger.error(f"Error applying additional filters: {e}")
            return df

    def get_search_suggestions(self, column_name: str, partial_value: str,
                               limit: int = 10) -> List[str]:
        """
        Get search suggestions untuk autocomplete.

        Args:
            column_name: Nama kolom
            partial_value: Sebagian nilai yang diketik user
            limit: Maksimal suggestions

        Returns:
            List suggestions
        """
        try:
            searchable_columns = self.get_all_searchable_columns()
            if column_name not in searchable_columns:
                return []

            column_meta = searchable_columns[column_name]

            if column_meta['type'] == 'static':
                db_column = column_meta['db_column']
                table = column_meta.get('table', 'user_terminals')

                query = f"""
                    SELECT DISTINCT {db_column}
                    FROM {table}
                    WHERE LOWER({db_column}) LIKE LOWER(%s)
                    AND {db_column} IS NOT NULL
                    ORDER BY {db_column}
                    LIMIT %s
                """

                data, columns, error = self.asset_data_service._execute_query(
                    query, (f"%{partial_value}%", limit))

                if error or not data:
                    return []

                return [row[0] for row in data if row[0]]

            else:  # dynamic column
                column_id = column_meta['column_id']

                query = """
                    SELECT DISTINCT column_value
                    FROM dynamic_column_data
                    WHERE column_id = %s
                    AND LOWER(column_value) LIKE LOWER(%s)
                    AND column_value IS NOT NULL
                    ORDER BY column_value
                    LIMIT %s
                """

                data, columns, error = self.asset_data_service._execute_query(
                    query, (column_id, f"%{partial_value}%", limit))

                if error or not data:
                    return []

                return [row[0] for row in data if row[0]]

        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []

    def clear_cache(self):
        """Clear internal caches."""
        self._column_cache.clear()
        self._search_cache.clear()
        logger.info("Search service cache cleared")

    def get_cached_comprehensive_base_query(self) -> str:
        """Get cached base comprehensive query to avoid rebuilding on every search."""
        import time

        current_time = time.time()
        cache_key = 'comprehensive_base'

        # Check if cache is valid
        if (cache_key in self._query_cache and
            'query' in self._query_cache[cache_key] and
            'timestamp' in self._query_cache[cache_key] and
                (current_time - self._query_cache[cache_key]['timestamp']) < self._query_cache_ttl):
            logger.debug("Using cached comprehensive base query")
            return self._query_cache[cache_key]['query']

        # Build new base query and cache it
        base_query = self.asset_data_service.build_comprehensive_query()
        # Remove ORDER BY to allow WHERE injection
        base_query_parts = base_query.strip().split('ORDER BY')
        clean_base_query = base_query_parts[0].strip()

        # Cache the result
        self._query_cache[cache_key] = {
            'query': clean_base_query,
            'timestamp': current_time
        }

        logger.info("Built and cached comprehensive base query")
        return clean_base_query

    def _enrich_with_dynamic_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich search results with dynamic columns data.

        Args:
            df: DataFrame with search results

        Returns:
            DataFrame enriched with dynamic columns
        """
        if df.empty:
            return df

        try:
            # Get all dynamic columns
            dynamic_columns = self.asset_data_service.column_manager.get_dynamic_columns(
                'user_terminals', active_only=True)

            if not dynamic_columns:
                return df

            # Get FAT IDs from the results
            fat_id_column = None
            for col in ['fat_id', 'FATID']:
                if col in df.columns:
                    fat_id_column = col
                    break

            if fat_id_column is None:
                logger.warning(
                    "No FAT ID column found for dynamic column enrichment")
                return df

            fat_ids = df[fat_id_column].dropna().unique().tolist()
            if not fat_ids:
                return df

            # Query dynamic column data
            placeholders = ','.join(['%s'] * len(fat_ids))
            query = f"""
                SELECT dcd.record_id, dc.display_name, dcd.column_value
                FROM dynamic_column_data dcd
                JOIN dynamic_columns dc ON dcd.column_id = dc.id
                WHERE dcd.record_id IN ({placeholders})
                AND dc.is_active = TRUE
                AND dcd.column_value IS NOT NULL
                AND dcd.column_value != ''
            """

            data, columns, error = self.asset_data_service._execute_query(
                query, tuple(fat_ids))

            if error:
                logger.warning(f"Error fetching dynamic columns data: {error}")
                return df

            if not data:
                return df

            # Convert to DataFrame and pivot
            dynamic_df = pd.DataFrame(data, columns=columns)
            dynamic_pivot = dynamic_df.pivot(
                index='record_id',
                columns='display_name',
                values='column_value'
            ).fillna('')

            # Reset index to make record_id a column
            dynamic_pivot = dynamic_pivot.reset_index()

            # Merge with original DataFrame
            enriched_df = df.merge(
                dynamic_pivot,
                left_on=fat_id_column,
                right_on='record_id',
                how='left'
            )

            # Drop the duplicate record_id column
            if 'record_id' in enriched_df.columns:
                enriched_df = enriched_df.drop('record_id', axis=1)

            # Fill NaN values in dynamic columns with empty strings
            dynamic_column_names = [col['display_name']
                                    for col in dynamic_columns]
            for col_name in dynamic_column_names:
                if col_name in enriched_df.columns:
                    enriched_df[col_name] = enriched_df[col_name].fillna('')

            logger.info(
                f"Enriched {len(enriched_df)} results with {len(dynamic_column_names)} dynamic columns")
            return enriched_df

        except Exception as e:
            logger.error(f"Error enriching with dynamic columns: {e}")
            return df


# Global instance (akan diinisialisasi dari controller)
unified_search_service = None


def get_unified_search_service(asset_data_service: AssetDataService) -> UnifiedSearchService:
    """Get or create unified search service instance."""
    global unified_search_service
    if unified_search_service is None:
        unified_search_service = UnifiedSearchService(asset_data_service)
    return unified_search_service

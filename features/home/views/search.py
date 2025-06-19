# features/home/views/search.py
import streamlit as st
from core.services.AssetDataService import AssetDataService  # Import service
import pandas as pd
import logging
from core.utils.database import connect_db
from core.services.dynamic_search_helper import get_unified_search_service

# Configure logging
logger = logging.getLogger(__name__)


def _get_dynamic_column_type(field_name: str, asset_data_service: AssetDataService) -> str:
    """
    Get the column type for a dynamic column field.

    Args:
        field_name: Display name of the field
        asset_data_service: AssetDataService instance

    Returns:
        Column type string ('TEXT', 'INTEGER', 'DECIMAL', 'DATE', 'BOOLEAN', 'URL')
    """
    try:
        dynamic_columns = asset_data_service.column_manager.get_dynamic_columns(
            'user_terminals', active_only=True)

        for col in dynamic_columns:
            if col.get('display_name') == field_name or col.get('column_name') == field_name:
                return col.get('column_type', 'TEXT')

        # Default to TEXT for static columns or unknown fields
        return 'TEXT'

    except Exception as e:
        logger.warning(
            f"Error getting dynamic column type for {field_name}: {e}")
        return 'TEXT'


def _render_appropriate_input_widget(field_name: str, current_value: str, input_key: str,
                                     asset_data_service: AssetDataService, disabled: bool = False):
    """
    Render the appropriate input widget based on field type.

    Args:
        field_name: Display name of the field
        current_value: Current value to display
        input_key: Streamlit session state key for the input
        asset_data_service: AssetDataService instance
        disabled: Whether the input should be disabled
    """
    try:
        # Get column type for dynamic columns
        column_type = _get_dynamic_column_type(field_name, asset_data_service)

        # Handle different input types based on column_type
        if column_type == 'INTEGER':
            try:
                int_value = int(
                    float(current_value)) if current_value and current_value != '-' else 0
            except (ValueError, TypeError):
                int_value = 0
            st.number_input(
                label=f"Edit {field_name}",
                value=int_value,
                step=1,
                key=input_key,
                disabled=disabled,
                label_visibility="collapsed"
            )

        elif column_type == 'DECIMAL':
            try:
                float_value = float(
                    current_value) if current_value and current_value != '-' else 0.0
            except (ValueError, TypeError):
                float_value = 0.0
            st.number_input(
                label=f"Edit {field_name}",
                value=float_value,
                step=0.01,
                format="%.2f",
                key=input_key,
                disabled=disabled,
                label_visibility="collapsed"
            )

        elif column_type == 'DATE':
            try:
                from datetime import datetime, date
                if current_value and current_value != '-':
                    if isinstance(current_value, str):
                        # Try to parse date string
                        try:
                            date_value = datetime.strptime(
                                current_value, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                date_value = datetime.strptime(
                                    current_value, '%d/%m/%Y').date()
                            except ValueError:
                                date_value = date.today()
                    else:
                        date_value = current_value if isinstance(
                            current_value, date) else date.today()
                else:
                    date_value = date.today()
            except Exception:
                date_value = date.today()

            st.date_input(
                label=f"Edit {field_name}",
                value=date_value,
                key=input_key,
                disabled=disabled,
                label_visibility="collapsed"
            )

        elif column_type == 'BOOLEAN':
            bool_value = str(current_value).lower() in (
                'true', '1', 'yes', 'ya', 'aktif') if current_value and current_value != '-' else False
            st.checkbox(
                label=f"Edit {field_name}",
                value=bool_value,
                key=input_key,
                disabled=disabled,
                label_visibility="collapsed"
            )

        elif column_type == 'URL':
            st.text_input(
                label=f"Edit {field_name} (URL)",
                value=current_value,
                placeholder="https://example.com",
                key=input_key,
                disabled=disabled,
                label_visibility="collapsed"
            )

        else:  # Default to TEXT
            st.text_input(
                label=f"Edit {field_name}",
                value=current_value,
                key=input_key,
                disabled=disabled,
                label_visibility="collapsed"
            )

    except Exception as e:
        logger.error(f"Error rendering input widget for {field_name}: {e}")
        # Fallback to text input
        st.text_input(
            label=f"Edit {field_name}",
            value=current_value,
            key=input_key,
            disabled=disabled,
            label_visibility="collapsed"
        )


def get_complete_column_mapping(asset_data_service: AssetDataService) -> dict:
    """
    Get complete column mapping including static and dynamic columns.
    Returns comprehensive mapping to ensure consistency across all search functions.
    Auto-detects all columns from database without hardcoding.

    Args:
        asset_data_service: AssetDataService instance

    Returns:
        Dictionary mapping database column names to display names
    """

    def _generate_display_name(db_column: str) -> str:
        """Convert database column name to display name using common patterns."""
        # Special cases that don't follow the pattern
        special_cases = {
            'fat_id': 'FATID',
            'fdt_id': 'FDT ID',
            'olt': 'OLT',
            'hc_old': 'HC Old',
            'hc_icrm': 'HC ICRM',
            'total_hc': 'Total HC',
            'cleansing_hp': 'Cleansing HP',
            'pa': 'PA',
            'up3': 'UP3',
            'ulp': 'ULP',
            'kota_kab': 'Kota/Kab',
            'status_osp_amarta_fat': 'Status OSP AMARTA FAT',
            'fat_id_x': 'FAT ID X'
        }

        if db_column in special_cases:
            return special_cases[db_column]

        # Auto-generate display name from database column
        return db_column.replace('_', ' ').title()

    # Initialize mapping dictionary
    column_mapping = {}

    # First, get dynamic columns with their configured display names
    # These take priority over auto-generated names
    dynamic_columns_map = {}
    try:
        dynamic_columns = asset_data_service.column_manager.get_dynamic_columns(
            'user_terminals', active_only=True)
        for col in dynamic_columns:
            column_name = col.get('column_name', '')
            display_name = col.get('display_name', column_name)
            if column_name and display_name:
                dynamic_columns_map[column_name] = display_name
                logger.info(
                    f"Dynamic column detected: {column_name} -> {display_name}")
    except Exception as e:
        logger.warning(f"Could not load dynamic columns for mapping: {e}")

    # Get all actual columns from database by loading sample data
    try:
        sample_data = asset_data_service.load_comprehensive_asset_data(limit=1)
        if sample_data is not None and not sample_data.empty:
            logger.info(
                f"Auto-detecting columns from database. Found {len(sample_data.columns)} columns.")

            for col in sample_data.columns:
                if col in dynamic_columns_map:
                    # Use configured display name for dynamic columns
                    column_mapping[col] = dynamic_columns_map[col]
                    logger.info(
                        f"Using dynamic column name: {col} -> {dynamic_columns_map[col]}")
                else:
                    # Auto-generate display name for regular columns
                    display_name = _generate_display_name(col)
                    column_mapping[col] = display_name

            logger.info(
                f"Generated {len(column_mapping)} column mappings automatically")

        else:
            logger.warning("No sample data available, using fallback mappings")
            # Fallback to essential mappings only
            column_mapping = {
                'fat_id': 'FATID',
                'olt': 'OLT',
                'fdt_id': 'FDT ID',
                'tanggal_rfs': 'Tanggal RFS',
                'kota_kab': 'Kota/Kab'
            }
            # Add dynamic columns to fallback
            column_mapping.update(dynamic_columns_map)

    except Exception as e:
        logger.error(f"Error generating dynamic column mapping: {e}")
        # Fallback to essential mappings
        column_mapping = {
            'fat_id': 'FATID',
            'olt': 'OLT',
            'fdt_id': 'FDT ID',
            'tanggal_rfs': 'Tanggal RFS',
            'kota_kab': 'Kota/Kab'
        }
        # Add dynamic columns to fallback
        column_mapping.update(dynamic_columns_map)

    logger.info(f"Final column mapping contains {len(column_mapping)} entries")
    return column_mapping


def render_editable_grid(filtered_items, table, pk_col, pk_val, asset_data_service, tab_context="main"):
    """
    Render editable grid for displaying and editing data fields.

    Args:
        filtered_items: Dictionary of field names and values
        table: Table name for database operations
        pk_col: Primary key column name
        pk_val: Primary key value
        asset_data_service: AssetDataService instance for updates
        tab_context: Context identifier to make keys unique across tabs
    """
    # Column mapping untuk konversi display name ke database column name
    display_to_db_column = {
        "FATID": "fat_id",
        "OLT": "olt",
        "FDT ID": "fdt_id"
    }    # Convert display column name to database column name
    db_pk_col = display_to_db_column.get(pk_col, pk_col.lower())

    keys = list(filtered_items.keys())
    n = len(keys)

    for i in range(0, n, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx >= n:
                break

            field = keys[idx]
            val = filtered_items[field]
            val = "-" if val is None or str(val) == "nan" else str(val)

            # Create unique keys by including tab context
            edit_key = f"edit_{tab_context}_{field}"
            input_key = f"input_{tab_context}_{field}"
            save_key = f"save_{tab_context}_{field}"
            btn_key = f"btn_{tab_context}_{field}"

            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            with cols[j]:
                st.markdown(f"**{field}**")
                c1, c2 = st.columns([10, 2])

                with c1:
                    if not st.session_state[edit_key]:
                        if isinstance(val, str) and val.startswith("http"):
                            st.markdown(
                                f"<a href='{val}' target='_blank' style='color: #1a73e8; text-decoration: underline;'>{val}</a>",
                                unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span>{val}</span>",
                                        unsafe_allow_html=True)
                    else:
                        # Determine input type based on field type (for dynamic columns)
                        _render_appropriate_input_widget(
                            field, val, input_key, asset_data_service,
                            disabled=not st.session_state[edit_key]
                        )

                with c2:
                    if st.session_state[edit_key]:
                        if st.button("💾", key=save_key):
                            new_val = st.session_state.get(input_key, "")

                            # Use AssetDataService comprehensive update
                            error = asset_data_service.update_asset_comprehensive(
                                db_pk_col, pk_val, {field: new_val})

                            if error:
                                st.error(f"Gagal mengupdate data: {error}")
                            else:
                                st.session_state.data_result.at[st.session_state.selected_index,
                                                                field] = new_val
                                st.session_state[edit_key] = False
                                st.success("Data berhasil diupdate!")
                                st.rerun()
                    else:
                        if st.button("✏️", key=btn_key):
                            st.session_state[edit_key] = True
                            st.rerun()


def search_assets_unified(asset_data_service: AssetDataService, search_params: dict) -> pd.DataFrame:
    """
    Fungsi search holistik yang menggunakan UnifiedSearchService.

    Args:
        asset_data_service: Instance AssetDataService
        search_params: Parameter pencarian

    Returns:
        DataFrame hasil pencarian dengan column mapping yang konsisten
    """
    try:
        # Get unified search service
        search_service = get_unified_search_service(
            asset_data_service)        # Execute unified search
        result_df = search_service.search_unified(search_params)

        if result_df is None or result_df.empty:
            logger.info("No results found in unified search")
            # Apply minimal column renaming (mostly keep original names + dynamic columns)
            return pd.DataFrame()        # Debug: Log columns before mapping
        logger.info(f"Columns before mapping: {list(result_df.columns)}")
        if 'tanggal_rfs' in result_df.columns:
            logger.info("✅ 'tanggal_rfs' column found in raw data")
            # Show sample tanggal_rfs data
            sample_tanggal_rfs = result_df['tanggal_rfs'].head().tolist()
            logger.info(f"Sample tanggal_rfs values: {sample_tanggal_rfs}")
        else:
            logger.warning("❌ 'tanggal_rfs' column NOT found in raw data")

        column_rename_map = asset_data_service.get_column_mapping()

        # Apply renaming only for specific mapped columns
        result_df.rename(columns=column_rename_map, inplace=True)

        # Debug: Log column mapping results
        logger.info(
            f"Applied column mapping. Columns after rename: {list(result_df.columns)}")
        if 'Tanggal RFS' in result_df.columns:
            logger.info("✅ 'Tanggal RFS' column found after mapping")
            # Show sample Tanggal RFS data after mapping
            sample_tanggal_rfs_mapped = result_df['Tanggal RFS'].head(
            ).tolist()
            logger.info(
                f"Sample 'Tanggal RFS' values after mapping: {sample_tanggal_rfs_mapped}")
        else:
            logger.warning("❌ 'Tanggal RFS' column NOT found after mapping")
            # Check if original column exists
            if 'tanggal_rfs' in column_rename_map:
                logger.info(
                    f"Original 'tanggal_rfs' was in mapping: {column_rename_map['tanggal_rfs']}")
            else:
                logger.warning("'tanggal_rfs' not found in column mapping")

        # Dynamic columns are now automatically included in the query results
        # No need to manually add them anymore since we use SELECT ut.*
        logger.info(
            f"Result has {len(result_df.columns)} columns after mapping")

        # Debug: Check if dynamic columns are included
        dynamic_cols_in_result = [col for col in result_df.columns if any(
            test_col in col.lower() for test_col in ['test', 'dynamic'])]
        if dynamic_cols_in_result:
            logger.info(
                f"Dynamic columns found in results: {dynamic_cols_in_result}")
        else:
            logger.info(
                "No dynamic columns found in results (this may be normal)")

        logger.info(
            f"Unified search returned {len(result_df)} results with column mapping applied")
        return result_df

    except Exception as e:
        logger.error(f"Error in unified search: {e}")
        return pd.DataFrame()


def get_search_suggestions(asset_data_service: AssetDataService, column_name: str, partial_value: str) -> list:
    """
    Mendapatkan suggestions untuk autocomplete search.

    Args:
        asset_data_service: Instance AssetDataService
        column_name: Nama kolom
        partial_value: Sebagian nilai yang diketik

    Returns:
        List suggestions
    """
    try:
        search_service = get_unified_search_service(asset_data_service)
        suggestions = search_service.get_search_suggestions(
            column_name, partial_value, limit=10)
        return suggestions
    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        return []


def fetch_data_by_search(asset_data_service: AssetDataService, search_column: str, search_value: str, additional_filters: dict = None) -> pd.DataFrame:
    """
    Optimized search that uses database-level filtering instead of loading all data.

    Args:
        asset_data_service: Instance of AssetDataService
        search_column: Column to search in
        search_value: Value to search for
        additional_filters: Additional filters to apply

    Returns:
        DataFrame with search results
    """

    try:
        # Map display column names to database column names
        display_to_db_column_map = {
            "FATID": "fat_id",
            "OLT": "olt",
            "FDT ID": "fdt_id"
        }
        # Convert display column name to database column name
        db_search_column = display_to_db_column_map.get(
            search_column, search_column.lower().replace(' ', '_'))

        # Use optimized database search instead of loading all data and filtering
        logger.info(
            f"Performing database search for {search_column}={search_value}")

        # Use database-level filtering for much better performance
        search_result = perform_optimized_search(
            asset_data_service, db_search_column, search_value)

        if search_result is None or search_result.empty:
            logger.warning(
                f"No results found for {search_column}={search_value}")
            return pd.DataFrame()

        logger.info(f"Search returned {len(search_result)} results")

        # Apply column rename mapping for consistency
        column_rename_map = asset_data_service.get_column_mapping()
        search_result.rename(columns=column_rename_map, inplace=True)

        return search_result
    except Exception as e:
        # Fallback to unified search
        logger.error(f"Error in optimized search: {e}")
        logger.warning("Falling back to unified search")
        search_params = {
            'primary_column': search_column,
            'primary_value': search_value,
            'additional_filters': additional_filters or {},
            'search_mode': 'auto',
            'limit': 1000
        }
        return search_assets_unified(asset_data_service, search_params)


# Legacy function - replaced by unified search system
def fetch_data_by_search_comprehensive(asset_data_service: AssetDataService, search_column: str, search_value: str, additional_filters: dict = None) -> pd.DataFrame:
    """
    DEPRECATED: This function has been replaced by the unified search system.
    Use search_assets_unified instead for better performance and functionality.
    """
    logger.warning(
        "fetch_data_by_search_comprehensive is deprecated. Using unified search instead.")

    search_params = {
        'primary_column': search_column,
        'primary_value': search_value,
        'additional_filters': additional_filters or {},
        'search_mode': 'auto',
        'limit': 1000
    }
    return search_assets_unified(asset_data_service, search_params)


def export_search_results(df: pd.DataFrame, filename_prefix: str = "search_results") -> bytes:
    """
    Export search results to Excel format.

    Args:
        df: DataFrame to export
        filename_prefix: Prefix for filename

    Returns:
        Excel file as bytes
    """
    try:
        from io import BytesIO
        import datetime

        # Try to import openpyxl, fallback to CSV if not available
        try:
            import openpyxl
            use_excel = True
        except ImportError:
            logger.warning(
                "openpyxl not available, falling back to CSV export")
            use_excel = False

        if use_excel:
            output = BytesIO()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Search Results', index=False)

                # Summary sheet
                summary_data = {
                    'Metric': ['Total Records', 'Export Date', 'Columns Count'],
                    'Value': [len(df), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(df.columns)]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            output.seek(0)
            return output.read()
        else:
            # Fallback to CSV
            output = BytesIO()
            csv_data = df.to_csv(index=False)
            output.write(csv_data.encode('utf-8'))
            output.seek(0)
            return output.read()

    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return None


def create_quick_filters(df: pd.DataFrame) -> dict:
    """
    Create quick filter options based on data.

    Args:
        df: DataFrame to analyze

    Returns:
        Dictionary of quick filter options
    """
    try:
        quick_filters = {}

        # Location-based filters
        if 'Kota/Kab' in df.columns:
            top_cities = df['Kota/Kab'].value_counts().head(5).index.tolist()
            quick_filters['top_cities'] = top_cities

        # Brand filters
        if 'Brand OLT' in df.columns:
            brands = df['Brand OLT'].value_counts().head(5).index.tolist()
            quick_filters['top_brands'] = brands

        # Status filters
        if 'FAT KONDISI' in df.columns:
            conditions = df['FAT KONDISI'].unique().tolist()
            quick_filters['fat_conditions'] = [
                c for c in conditions if pd.notna(c)]

        return quick_filters
    except Exception as e:
        logger.error(f"Error creating quick filters: {e}")
        return {}


def app(asset_data_service: AssetDataService):
    """
    Provides an interface to search for specific assets in the database.
    (Currently a placeholder).

    Args:
        asset_data_service: An instance of AssetDataService to perform searches.
    """
    st.markdown("""
<style>
[data-testid="stSidebarNav"] {
display: ;
}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
    <style>
    .block-container {
        padding: 2rem 4rem;
        max-width: 100% !important;
    }
    .search-card {
        padding: 15px;
        border-bottom: 1px solid #ddd;
        margin-bottom: 15px;
        transition: background 0.2s ease-in-out;
    }
    .search-card:hover {
        background-color: #f4f4f4;
        cursor: pointer;
    }
    .search-card small {
        color: #666;
        font-size: 13px;
    }
    .search-card h4 {
        margin: 0.25rem 0 0.5rem 0;
        font-size: 18px;
    }
    .field-row {
        display: flex;
        flex-wrap: wrap;
        gap: 30px;
        margin-top: 10px;
    }
    .field-item {
        font-size: 14px;
        color: #444;
        min-width: 180px;
        white-space: nowrap;
    }
    .detail-section {
        margin-top: 1.5rem;
    }
    .detail-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr); /* Grid 3 kolom */
        gap: 0.5rem 1rem; /* Memperkecil jarak antar kolom */
        font-family: 'Segoe UI', sans-serif;
        margin-top: 1rem;
    }
    .detail-item {
        margin-bottom: 0.5rem;
    }
    .detail-label {
        font-weight: bold;
        color: #333;
        font-size: 14px;
        margin-bottom: 0.1rem;  /* sebelumnya 2px atau lebih besar, dikurangi agar lebih rapat */
    }

    .detail-value {
        font-size: 14px;
        color: #111;
        margin-top: 0rem;        /* hilangkan jarak atas */
        padding-top: 0rem;
        display: inline-block;
        vertical-align: middle;
    }
    /* Tombol edit yang lebih natural */
    .edit-icon {
        color: #2196F3;
        font-size: 18px;
        cursor: pointer;
        display: inline-block;
        vertical-align: middle;
        padding-left: 8px;
    }

    /* Form Input Field styling */
    .stTextInput > div > input {
        font-size: 14px;
        padding: 4px 6px;
    }
    /* Mode edit (input aktif) */
    input:not([disabled]),
    textarea:not([disabled]) {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* Mode disabled (tidak bisa di-edit) */
    # input[disabled],
    # textarea[disabled] {
    #     color: #707070 !important;
    #     -webkit-text-fill-color: #707070 !important;
    #     opacity: 1 !important;  /* memastikan tidak terlihat transparan */
    # }
    /* Styling untuk header dan tab */
    .stTabs {
        margin-top: 0.5rem;
    }
    .stTabs__tab {
        font-size: 14px;
    }

    /* Untuk tabs tambahan informasi */
    .detail-section {
        margin-top: 1rem;
    }    </style>
""", unsafe_allow_html=True)

    if "selected_index" not in st.session_state:
        st.session_state.selected_index = None
    if "data_result" not in st.session_state:
        st.session_state.data_result = pd.DataFrame()
    if "search_submitted" not in st.session_state:
        st.session_state.search_submitted = False

    # Back Button - hanya tampil ketika dalam detail view
    if st.session_state.selected_index is not None:
        st.markdown("<div style='margin-top: 1.5rem;'>",
                    unsafe_allow_html=True)
        if st.button("←", use_container_width=False):
            st.session_state.selected_index = None
            st.rerun()  # ⬅️ ini memastikan halaman refresh dan tombol langsung hilang
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center;'>🔍 Data Asset Information</h2>",
                unsafe_allow_html=True)

    main_filters = {
        "OLT": {
            "column": "OLT",
            "attributes": ["Brand OLT", "Type OLT", "Latitude OLT", "Longitude OLT", "Kota/Kab", "FATID", "Hostname OLT", "Kapasitas OLT", "Interface OLT"]
        },        "FAT ID": {
            "column": "FATID",
            "attributes": ["Latitude FAT", "Longitude FAT", "Kecamatan", "Kelurahan", "OLT", "FAT KONDISI", "FILTER FAT CAP", "Jumlah Splitter FAT", "Kapasitas FAT", "Total HC"]
        },
        "FDT ID": {
            "column": "FDT ID",
            "attributes": ["Koordinat FDT", "FATID", "Koordinat Cluster", "Cluster", "Kota/Kab"]
        }
    }

    col1, col2 = st.columns([1, 4])
    with col1:
        main_filter = st.selectbox(
            "Filter Utama:", list(main_filters.keys()), index=0)

    with col2:
        search_input = st.text_input("Masukkan kata kunci pencarian",
                                     help="Ketik kata kunci untuk mencari data asset")

        # Show search suggestions if there's partial input
        if search_input and len(search_input) >= 2:
            selected_column = main_filters[main_filter]["column"]
            try:
                suggestions = get_search_suggestions(
                    asset_data_service, selected_column, search_input)
                if suggestions:
                    with st.expander("💡 Saran Pencarian", expanded=True):
                        suggestion_cols = st.columns(min(3, len(suggestions)))
                        # Limit to 6 suggestions
                        for i, suggestion in enumerate(suggestions[:6]):
                            col_idx = i % 3
                            with suggestion_cols[col_idx]:
                                if st.button(f"📌 {suggestion}", key=f"suggestion_{i}",
                                             help=f"Klik untuk mencari: {suggestion}"):
                                    st.session_state['search_input_suggested'] = suggestion
                                    st.rerun()
            except Exception as e:
                logger.warning(f"Could not load search suggestions: {e}")
          # Handle suggested search input
        if 'search_input_suggested' in st.session_state:
            search_input = st.session_state['search_input_suggested']
            del st.session_state['search_input_suggested']

    selected_column = main_filters[main_filter]["column"]
    attribute_filters = main_filters[main_filter]["attributes"]

    # Advanced Search Options
    col_mode, col_limit = st.columns([2, 1])
    with col_mode:
        search_mode = st.selectbox(
            "Mode Pencarian:",
            ["Auto (Cerdas)", "Exact Match", "Partial Match"],
            help="Auto: mencoba exact match dulu, lalu partial. Exact: hanya hasil yang sama persis. Partial: hasil yang mengandung kata kunci"
        )
    with col_limit:
        search_limit = st.number_input(
            "Maksimal Hasil:",
            min_value=10,
            max_value=5000,
            value=1000,
            step=50,
            help="Batasi jumlah hasil pencarian untuk performa yang lebih baik"
        )    # Convert search mode to internal format
    mode_mapping = {
        "Auto (Cerdas)": "auto",
        "Exact Match": "exact",
        "Partial Match": "partial"
    }
    internal_search_mode = mode_mapping[search_mode]

    with st.expander("🔧 Filter Tambahan (Opsional)", expanded=False):
        additional_filters = {}

        # Create columns for better layout of additional filters
        filter_cols = st.columns(2)
        for i, attr in enumerate(attribute_filters):
            col_idx = i % 2
            with filter_cols[col_idx]:
                user_input = st.text_input(f"🔍 {attr}:", key=f"filter_{attr}")
                if user_input:
                    additional_filters[attr] = user_input

        # Get available dynamic columns for additional filtering
        try:
            search_service = get_unified_search_service(asset_data_service)
            searchable_columns = search_service.get_all_searchable_columns()
            dynamic_columns = [name for name, meta in searchable_columns.items()
                               if meta['type'] == 'dynamic']

            if dynamic_columns:
                st.markdown("**📊 Filter Kolom Dinamis:**")
                dynamic_filter_cols = st.columns(2)
                # Limit to 4 dynamic filters
                for i, col_name in enumerate(dynamic_columns[:4]):
                    col_idx = i % 2
                    with dynamic_filter_cols[col_idx]:
                        user_input = st.text_input(
                            f"🎯 {col_name}:", key=f"dynamic_filter_{col_name}")
                        if user_input:
                            additional_filters[col_name] = user_input
        except Exception as e:
            # Search Button with improved styling
            logger.warning(
                f"Could not load dynamic columns for filtering: {e}")
    search_col1, search_col2, search_col3 = st.columns([2, 1, 2])
    with search_col2:
        search_clicked = st.button(
            "🔍 **SEARCH**", type="primary", use_container_width=True)

    if search_clicked and search_input:
        with st.spinner("🔍 Mencari data asset..."):
            # Prepare search parameters for unified search
            search_params = {
                'primary_column': selected_column,
                'primary_value': search_input,
                'additional_filters': additional_filters,
                'search_mode': internal_search_mode,
                'limit': int(search_limit)
            }

            # Use unified search
            result_df = search_assets_unified(
                asset_data_service, search_params)
            st.session_state.data_result = result_df
            st.session_state.selected_index = None
            st.session_state.search_submitted = True
            # Show search summary
            if not result_df.empty:
                st.success(
                    f"✅ Ditemukan {len(result_df)} hasil untuk pencarian '{search_input}' di kolom {selected_column}")
            else:
                st.warning(
                    f"❌ Tidak ditemukan hasil untuk pencarian '{search_input}' di kolom {selected_column}")
                if additional_filters:
                    st.info(
                        "💡 Coba kurangi filter tambahan atau gunakan kata kunci yang berbeda")

    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    if "page_size" not in st.session_state:
        st.session_state.page_size = 50
    data = st.session_state.data_result

    if st.session_state.selected_index is None:
        if not data.empty:
            # Results Header with Quick Actions
            result_col1, result_col2, result_col3 = st.columns([2, 1, 1])

            with result_col1:
                st.markdown(
                    f"<p><strong>📊 Ditemukan {len(data)} data</strong></p>", unsafe_allow_html=True)

            with result_col2:
                # Export functionality with fallback
                try:
                    # Check if openpyxl is available
                    try:
                        export_format = "Excel"
                        file_extension = "xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    except ImportError:
                        export_format = "CSV"
                        file_extension = "csv"
                        mime_type = "text/csv"

                    exported_data = export_search_results(
                        data, "search_results")
                    if exported_data:
                        st.download_button(
                            label=f"📥 Export {export_format}",
                            data=exported_data,
                            file_name=f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}",
                            mime=mime_type,
                            help=f"Download hasil pencarian dalam format {export_format}"
                        )
                    else:
                        st.error("❌ Export gagal")
                except Exception as e:
                    logger.warning(f"Export functionality not available: {e}")
                    # Fallback: Simple CSV export
                    try:
                        csv_data = data.to_csv(index=False)
                        st.download_button(
                            label="📥 Export CSV",
                            data=csv_data,
                            file_name=f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            help="Download hasil pencarian dalam format CSV"
                        )
                    except Exception as csv_error:
                        logger.error(f"CSV export also failed: {csv_error}")

            with result_col3:
                # Quick action: Clear results
                if st.button("🗑️ Clear", help="Hapus hasil pencarian"):
                    st.session_state.data_result = pd.DataFrame()
                    st.session_state.search_submitted = False
                    st.rerun()

            # Quick Filters
            try:
                quick_filters = create_quick_filters(data)
                if quick_filters:
                    with st.expander("⚡ Quick Filters", expanded=False):
                        filter_applied = False

                        if quick_filters.get('top_cities'):
                            st.markdown(
                                "**🏙️ Filter berdasarkan Kota/Kab Populer:**")
                            city_cols = st.columns(
                                min(3, len(quick_filters['top_cities'])))
                            for i, city in enumerate(quick_filters['top_cities']):
                                with city_cols[i % 3]:
                                    if st.button(f"📍 {city}", key=f"qf_city_{i}"):
                                        filtered_data = data[data['Kota/Kab'].str.contains(
                                            str(city), na=False, case=False)]
                                        st.session_state.data_result = filtered_data
                                        filter_applied = True

                        if quick_filters.get('top_brands'):
                            st.markdown("**🏭 Filter berdasarkan Brand OLT:**")
                            brand_cols = st.columns(
                                min(3, len(quick_filters['top_brands'])))
                            for i, brand in enumerate(quick_filters['top_brands']):
                                with brand_cols[i % 3]:
                                    if st.button(f"🔧 {brand}", key=f"qf_brand_{i}"):
                                        filtered_data = data[data['Brand OLT'].str.contains(
                                            str(brand), na=False, case=False)]
                                        st.session_state.data_result = filtered_data
                                        filter_applied = True

                        if filter_applied:
                            st.rerun()
            except Exception as e:
                logger.warning(f"Quick filters not available: {e}")

            # Sorting Options
            sort_col1, sort_col2 = st.columns([2, 1])
            with sort_col1:
                sort_order = st.radio("📊 Urutkan berdasarkan:", [
                                      "Terbaru", "Terlama"], horizontal=True, key="sort")
            with sort_col2:
                # Additional sorting options
                if st.button("🔄 Reset Sort"):
                    # Reset to original data order
                    st.session_state.data_result = st.session_state.data_result.reset_index(
                        drop=True)
                    st.rerun()

            if "Tanggal RFS" in data.columns:
                data["Tanggal RFS"] = pd.to_datetime(
                    data["Tanggal RFS"], errors="coerce")
                data = data.sort_values(
                    by="Tanggal RFS", ascending=(sort_order == "Terlama"))

            # Pagination Settings
            page_size = 50  # Jumlah data per halaman
            total_pages = (len(data) - 1) // page_size + 1
            current_page = st.session_state.get("current_page", 1)

            def go_to_page(p):
                st.session_state.current_page = p
                st.rerun()            # Display Paginated Data
            paginated_data = data.iloc[(
                current_page - 1) * page_size: current_page * page_size]            # Debug: Log available columns for troubleshooting search card display
            logger.info(
                f"Available columns in search results: {list(data.columns)}")
            if not data.empty:
                first_row = data.iloc[0]
                logger.info(
                    f"Sample data - Tanggal RFS: {first_row.get('Tanggal RFS', 'NOT FOUND')}")
                logger.info(
                    f"Sample data - OLT: {first_row.get('OLT', 'NOT FOUND')}")
                logger.info(
                    f"Sample data - FATID: {first_row.get('FATID', 'NOT FOUND')}")

            # Create a mapping from paginated index to original index
            original_indices = data.iloc[(
                current_page - 1) * page_size: current_page * page_size].index.tolist()

            for idx, (original_idx, row) in enumerate(paginated_data.iterrows()):
                # Debug: Log available columns for this row
                with st.form(f"form_{original_idx}"):
                    logger.info(f"Row {idx} columns: {list(row.index)}")

                    # Try different possible column names for Tanggal RFS
                    tanggal_rfs_raw = None
                    possible_tanggal_keys = [
                        'Tanggal Rfs', 'Tanggal RFS', 'tanggal_rfs', 'TANGGAL_RFS']

                    for key in possible_tanggal_keys:
                        if key in row.index:
                            tanggal_rfs_raw = row.get(key)
                            logger.info(
                                f"Row {idx} found Tanggal RFS with key '{key}': {tanggal_rfs_raw}")
                            break

                    if tanggal_rfs_raw is None:
                        logger.info(
                            f"Row {idx} Tanggal RFS not found in any expected column names")
                        tanggal_rfs_raw = 'NOT_FOUND'

                    logger.info(
                        f"Row {idx} Tanggal RFS raw value: {tanggal_rfs_raw}")

                    # Format the Tanggal RFS for display
                    tanggal_rfs_display = tanggal_rfs_raw if tanggal_rfs_raw and tanggal_rfs_raw != 'NOT_FOUND' else '-'
                    logger.info(
                        f"Row {idx} tanggal_rfs_display initial: {tanggal_rfs_display}")

                    if tanggal_rfs_display != '-' and pd.notna(tanggal_rfs_display):
                        # Convert to string if it's a datetime object
                        if hasattr(tanggal_rfs_display, 'strftime'):
                            tanggal_rfs_display = tanggal_rfs_display.strftime(
                                '%Y-%m-%d')
                        else:
                            tanggal_rfs_display = str(tanggal_rfs_display)
                    else:
                        tanggal_rfs_display = '-'

                    logger.info(
                        f"Row {idx} tanggal_rfs_display final: {tanggal_rfs_display}")

                    markdown_content = f"""
                    <div class='search-card'>
                        <h4>{row.get(selected_column, 'Tanpa Nama')}</h4>
                        <small>{row.get('Kota/Kab', '-')}</small>
                        <div class='field-row'>
                            <div class='field-item'>
                                <strong>Tanggal RFS:</strong> 
                                <span style='color: green; background-color: #f8f9fa; padding: 2px 6px; border-radius: 6px; font-weight: 600;'>
                                    {tanggal_rfs_display}
                                </span>
                            </div>
                            <div class='field-item'><strong>OLT:</strong> {row.get('OLT', '-')}</div>
                            <div class='field-item'><strong>FAT ID:</strong> {row.get('FATID', '-')}</div>
                        </div>
                    </div>
                    """
                    st.markdown(markdown_content, unsafe_allow_html=True)
                    if st.form_submit_button("Lihat Detail", use_container_width=True):
                        # Reset semua state edit_*
                        for key in list(st.session_state.keys()):
                            if key.startswith("edit_"):
                                del st.session_state[key]

                        # Use position in the current data, not original DataFrame index
                        position_in_current_data = (
                            current_page - 1) * page_size + idx
                        st.session_state.selected_index = position_in_current_data
                        st.rerun()
            # Navigasi Pagination Streamlit Native
            st.markdown("---")
            pagination_col = st.columns([1, 8, 1])

            with pagination_col[0]:
                if st.button("⬅️ Prev") and current_page > 1:
                    st.session_state.current_page -= 1
                    st.rerun()

            with pagination_col[2]:
                if st.button("Next ➡️") and current_page < total_pages:
                    st.session_state.current_page += 1
                    st.rerun()            # Tampilkan range halaman sebagai teks tengah
            with pagination_col[1]:
                start_idx = (current_page - 1) * page_size + 1
                end_idx = min(current_page * page_size, len(data))
                st.markdown(
                    f"<div style='text-align:center; font-weight:bold;'>Menampilkan {start_idx}-{end_idx} dari {len(data)} data</div>", unsafe_allow_html=True)

        elif st.session_state.search_submitted and data.empty:
            st.warning("Tidak ditemukan hasil.")

    else:
        # ======================
        # Show Detail
        # ======================
        # Validate selected_index is within bounds
        if st.session_state.selected_index >= len(data):
            st.error("Index yang dipilih tidak valid. Kembali ke daftar pencarian.")
            st.session_state.selected_index = None
            st.rerun()        # Get the detail row data
        detail_row = data.iloc[st.session_state.selected_index]
        # Get all available columns and determine main detail section based on search column
        st.markdown("## 📝 Detail Data")
        all_columns = set(detail_row.keys())

        # DEBUG: Log semua kolom yang ada untuk investigasi
        logger.info(f"=== DEBUG: TOTAL KOLOM ANALYSIS ===")
        logger.info(f"Total columns found: {len(all_columns)}")
        # Check if this is comprehensive data (using display names and original names)
        logger.info(f"All columns: {sorted(list(all_columns))}")
        has_tanggal_rfs = any(col in all_columns for col in [
                              'Tanggal RFS', 'Tanggal Rfs', 'tanggal_rfs'])
        has_kota_kab = any(col in all_columns for col in [
                           'Kota/Kab', 'kota_kab'])

        if has_tanggal_rfs and has_kota_kab:
            logger.info(
                "✅ Comprehensive data detected (contains tanggal_rfs and kota_kab)")
        else:
            # This is just a warning, not an error - system is working correctly
            logger.info(
                f"ℹ️ Data check: has_tanggal_rfs={has_tanggal_rfs}, has_kota_kab={has_kota_kab}")

        main_detail_title = ""
        main_detail_data = {}

        if selected_column == "FATID" or selected_column == "fat_id":
            # FAT-based search - show FAT info as main detail
            main_detail_title = "📍 Detail Informasi FAT Utama"
            fat_main_fields = [k for k in all_columns if any(term in k.lower() for term in [
                'fat', 'splitter_fat', 'latitude_fat', 'longitude_fat', 'kondisi', 'filter_fat', 'fatid'])
                and 'olt' not in k.lower() and 'fdt' not in k.lower()]
            main_detail_data = {k: detail_row[k]
                                for k in fat_main_fields if k in detail_row}

        elif selected_column == "OLT" or 'olt' in selected_column.lower():
            # OLT-based search - show OLT info as main detail
            main_detail_title = "🔧 Detail Informasi OLT Utama"
            olt_main_fields = [k for k in all_columns if any(term in k.lower() for term in [
                'olt', 'hostname', 'brand_olt', 'type_olt', 'kapasitas_olt', 'interface_olt', 'port_olt'])
                and k not in ['fat_id', 'FATID']]
            main_detail_data = {k: detail_row[k]
                                for k in olt_main_fields if k in detail_row}

        elif selected_column == "FDT ID" or 'fdt' in selected_column.lower():
            # FDT-based search - show FDT info as main detail
            main_detail_title = "📦 Detail Informasi FDT Utama"
            fdt_main_fields = [k for k in all_columns if any(term in k.lower() for term in [
                'fdt', 'splitter_fdt', 'latitude_fdt', 'longitude_fdt', 'port_fdt'])
                and k not in ['fat_id', 'FATID']]
            main_detail_data = {k: detail_row[k]
                                for k in fdt_main_fields if k in detail_row}

        else:
            # Default - show core fields
            main_detail_title = "📝 Detail Informasi Utama"
            core_fields = ['FATID', 'fat_id', 'OLT', 'FDT ID']
            main_detail_data = {k: detail_row[k]
                                for k in core_fields if k in detail_row}

        # Check if any edit mode is active (with new key pattern)
        edit_mode_active = any(
            st.session_state.get(key, False)
            for key in st.session_state.keys()
            if key.startswith("edit_") and any(field in key for field in detail_row.keys())
        )

        col_title, col_button = st.columns([8, 2])

        with col_title:
            st.markdown(f"## {main_detail_title}")

        with col_button:
            col_cancel, col_delete = st.columns([1.3, 2])

            with col_cancel:
                cancel_disabled = not edit_mode_active
                if st.button("❌ Cancel", disabled=cancel_disabled):
                    # Reset all edit states with new key pattern
                    for key in list(st.session_state.keys()):
                        if key.startswith("edit_"):
                            st.session_state[key] = False
                    st.rerun()

            with col_delete:
                # Use AssetDataService comprehensive delete with confirmation
                if st.button("🗑️ Hapus Data"):
                    st.session_state.show_delete_confirmation = True

        # Show confirmation dialog OUTSIDE of nested columns
        if st.session_state.get('show_delete_confirmation', False):
            st.warning("⚠️ **Konfirmasi Penghapusan Data**")
            st.write(
                f"Apakah Anda yakin ingin menghapus data dengan {selected_column}: **{detail_row[selected_column]}**?")
            st.write("**Tindakan ini tidak dapat dibatalkan!**")

            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("✅ Ya, Hapus", type="primary", key="confirm_delete"):
                    # Map display column names to database column names for primary keys
                    display_to_db_column_map = {
                        "FATID": "fat_id",
                        "OLT": "olt",
                        "FDT ID": "fdt_id"}

                    # Convert display column name to database column name if needed
                    db_selected_column = display_to_db_column_map.get(
                        selected_column, selected_column.lower())

                    error = asset_data_service.delete_asset_comprehensive(
                        db_selected_column, detail_row[selected_column])
                    if error:
                        st.error(f"Gagal menghapus data: {error}")
                    else:
                        st.success("Data berhasil dihapus.")
                        st.session_state.selected_index = None

                    # Reset confirmation state
                    st.session_state.show_delete_confirmation = False
                    st.rerun()

            with col_cancel:
                if st.button("❌ Batal", key="cancel_delete"):
                    st.session_state.show_delete_confirmation = False
                    st.rerun()  # Dynamic approach: Show ALL available columns without hardcoding
        # Just organize them in logical groups for better UX

        # Define core/primary fields that should be shown first
        # Use the main detail data as core fields
        core_fields = list(main_detail_data.keys())

        # Categorize remaining columns by common patterns (more comprehensive)
        olt_columns = [k for k in all_columns if any(term in k.lower() for term in ['olt', 'hostname'])
                       and k not in core_fields]

        fat_columns = [k for k in all_columns if any(term in k.lower() for term in ['fat', 'splitter_fat', 'latitude_fat', 'longitude_fat', 'kondisi', 'filter_fat'])
                       and k not in core_fields and 'olt' not in k.lower() and 'fdt' not in k.lower()]

        fdt_columns = [k for k in all_columns if any(term in k.lower() for term in ['fdt', 'splitter_fdt', 'latitude_fdt', 'longitude_fdt'])
                       and k not in core_fields]

        cluster_columns = [k for k in all_columns if any(term in k.lower() for term in [
            'kota', 'kecamatan', 'kelurahan', 'cluster', 'area', 'koordinat_cluster', 'latitude_cluster', 'longitude_cluster', 'up3', 'ulp'])
            and k not in core_fields]

        hc_columns = [k for k in all_columns if any(term in k.lower() for term in ['hc', 'home', 'cleansing'])
                      and k not in core_fields]

        doc_columns = [k for k in all_columns if any(term in k.lower() for term in [
            'dok', 'link', 'maps', 'update', 'amarta', 'dokumen', 'data_aset', 'feeder'])
            and k not in core_fields]

        # Additional categories for better organization
        rfs_date_columns = [k for k in all_columns if any(term in k.lower() for term in [
            'tanggal', 'rfs', 'date']) and k not in core_fields]

        network_columns = [k for k in all_columns if any(term in k.lower() for term in [
            'interface', 'port', 'brand', 'type', 'kapasitas', 'mitra'])
            and k not in core_fields and k not in olt_columns and k not in fat_columns and k not in fdt_columns]

        status_columns = [k for k in all_columns if any(term in k.lower() for term in [
            'status', 'osp', 'existing', 'new', 'kategori', 'sumber'])
            and k not in core_fields and k not in doc_columns]

        coordinate_columns = [k for k in all_columns if any(term in k.lower() for term in [
            'latitude', 'longitude', 'koordinat'])
            and k not in core_fields and k not in olt_columns and k not in fat_columns and k not in fdt_columns and k not in cluster_columns]

        # Get dynamic columns separately
        dynamic_columns_data = {}
        try:
            dynamic_columns = asset_data_service.column_manager.get_dynamic_columns(
                'user_terminals', active_only=True)
            dynamic_column_names = {
                col.get('display_name', ''): col for col in dynamic_columns}
            dynamic_columns_data = {
                k: detail_row[k] for k in detail_row.keys() if k in dynamic_column_names}
        except Exception as e:
            logger.warning(f"Could not get dynamic columns: {e}")

        # Collect used fields to find remaining ones
        used_fields = set(core_fields + olt_columns + fat_columns + fdt_columns +
                          cluster_columns + hc_columns + doc_columns + rfs_date_columns +
                          network_columns + status_columns + coordinate_columns + list(dynamic_columns_data.keys()))

        # Remaining fields (everything else not categorized) - THIS ENSURES NO COLUMN IS MISSED
        remaining_fields = {k: detail_row[k]
                            for k in all_columns if k not in used_fields}
        # Log for debugging what columns might be missing
        if remaining_fields:
            logger.info(
                f"Remaining uncategorized columns: {list(remaining_fields.keys())}")

        # Log kategorisasi kolom untuk debugging
        logger.info(f"Total columns: {len(all_columns)}")
        logger.info(
            f"OLT columns: {len(olt_columns)} | FAT columns: {len(fat_columns)} | FDT columns: {len(fdt_columns)}")
        logger.info(
            f"Location columns: {len(cluster_columns)} | HC columns: {len(hc_columns)} | Doc columns: {len(doc_columns)}")
        logger.info(
            f"Date columns: {len(rfs_date_columns)} | Network columns: {len(network_columns)} | Status columns: {len(status_columns)}")
        logger.info(
            f"Coordinate columns: {len(coordinate_columns)} | Dynamic columns: {len(dynamic_columns_data)} | Remaining: {len(remaining_fields)}")

        # Create dynamic tab structure
        tab_structure = []
        tab_data_map = {}

        if olt_columns:
            tab_structure.append("OLT Info")
            tab_data_map["OLT Info"] = {k: detail_row[k]
                                        for k in olt_columns if k in detail_row}

        if fat_columns:
            tab_structure.append("FAT Info")
            tab_data_map["FAT Info"] = {k: detail_row[k]
                                        for k in fat_columns if k in detail_row}

        if fdt_columns:
            tab_structure.append("FDT Info")
            tab_data_map["FDT Info"] = {k: detail_row[k]
                                        for k in fdt_columns if k in detail_row}

        if cluster_columns:
            tab_structure.append("Location Info")
            tab_data_map["Location Info"] = {k: detail_row[k]
                                             for k in cluster_columns if k in detail_row}

        if hc_columns:
            tab_structure.append("Home Connected")
            tab_data_map["Home Connected"] = {
                k: detail_row[k] for k in hc_columns if k in detail_row}

        if rfs_date_columns:
            tab_structure.append("Tanggal & Waktu")
            tab_data_map["Tanggal & Waktu"] = {
                k: detail_row[k] for k in rfs_date_columns if k in detail_row}

        if network_columns:
            tab_structure.append("Network Info")
            tab_data_map["Network Info"] = {k: detail_row[k]
                                            for k in network_columns if k in detail_row}

        if status_columns:
            tab_structure.append("Status & Kategori")
            tab_data_map["Status & Kategori"] = {
                k: detail_row[k] for k in status_columns if k in detail_row}

        if coordinate_columns:
            tab_structure.append("Koordinat Lainnya")
            tab_data_map["Koordinat Lainnya"] = {
                k: detail_row[k] for k in coordinate_columns if k in detail_row}

        if doc_columns:
            tab_structure.append("Dokumentasi")
            tab_data_map["Dokumentasi"] = {k: detail_row[k]
                                           for k in doc_columns if k in detail_row}

        if dynamic_columns_data:
            tab_structure.append("Kolom Dinamis")
            # PENTING: Pastikan semua remaining fields ditampilkan di tab "Lainnya"
            tab_data_map["Kolom Dinamis"] = dynamic_columns_data
        if remaining_fields:
            tab_structure.append("Lainnya")
            tab_data_map["Lainnya"] = remaining_fields

        # TAMBAHAN: Tab "Semua Kolom" untuk memastikan tidak ada yang terlewat
        tab_structure.append("📋 Semua Kolom")
        # Safe way to get primary key value (needed for all render_editable_grid calls)
        tab_data_map["📋 Semua Kolom"] = {k: detail_row[k] for k in all_columns}
        primary_key_value = None
        if selected_column in detail_row:
            primary_key_value = detail_row[selected_column]
        elif 'fat_id' in detail_row:
            primary_key_value = detail_row['fat_id']
        elif 'FATID' in detail_row:
            primary_key_value = detail_row['FATID']
        else:
            # Get first available value as fallback
            primary_key_value = detail_row.iloc[0] if len(
                detail_row) > 0 else None        # Render informasi utama (main detail data)
        if main_detail_data:
            render_editable_grid(main_detail_data, "user_terminals",
                                 selected_column, primary_key_value, asset_data_service, "main")

        # Tabs untuk informasi tambahan
        st.markdown("<div style='margin-bottom: 2.5rem;'></div>",
                    unsafe_allow_html=True)

        st.markdown(
            f"<h4 style='margin-top: -1rem; margin-bottom: 0.5rem;'>📂 Semua Informasi Database ({len(all_columns)} kolom total)</h4>",
            unsafe_allow_html=True)

        if tab_structure:
            tabs = st.tabs(tab_structure)

            for tab, tab_name in zip(tabs, tab_structure):
                with tab:
                    tab_data = tab_data_map.get(tab_name, {})

                    if tab_data:
                        # Show count of columns in each tab
                        if tab_name == "📋 Semua Kolom":
                            st.info(
                                f"📊 Menampilkan SEMUA {len(tab_data)} kolom dari database (dalam urutan alfabetis)")
                            # Sort columns alphabetically for better organization
                            sorted_tab_data = dict(sorted(tab_data.items()))
                            render_editable_grid(
                                sorted_tab_data, "user_terminals", selected_column,
                                primary_key_value, asset_data_service, "all_columns")
                        elif tab_name == "Kolom Dinamis":
                            st.info(
                                f"💡 Menampilkan {len(tab_data)} kolom dinamis yang telah ditambahkan")
                            render_editable_grid(
                                tab_data, "user_terminals", selected_column,
                                primary_key_value, asset_data_service, "dynamic")
                        else:
                            st.info(
                                f"📋 {len(tab_data)} kolom dalam kategori {tab_name}")
                            # Create unique tab context based on tab name
                            tab_context = tab_name.lower().replace(" ", "_").replace(
                                "&", "").replace("📋", "").replace("🔧", "")
                            render_editable_grid(
                                tab_data, "user_terminals", selected_column,                                primary_key_value, asset_data_service, tab_context)
                    else:
                        if tab_name == "Kolom Dinamis":
                            st.info(
                                "Belum ada kolom dinamis yang ditambahkan. Gunakan menu 'Tambah Kolom' untuk menambahkan kolom baru.")
                        else:
                            st.info(
                                "Tidak ada informasi relevan untuk kategori ini.")
        else:
            st.warning("Tidak ada data tambahan untuk ditampilkan.")


def perform_optimized_search(asset_data_service: AssetDataService, search_column: str, search_value: str) -> pd.DataFrame:
    """
    Perform optimized database search with WHERE clause instead of loading all data.

    Args:
        asset_data_service: AssetDataService instance
        search_column: Database column name to search
        search_value: Value to search for

    Returns:
        DataFrame with search results
    """
    try:
        # Build optimized query with WHERE clause at database level
        base_query = asset_data_service.build_comprehensive_query()

        # Remove ORDER BY to inject WHERE clause
        base_query_parts = base_query.strip().split('ORDER BY')
        select_and_joins = base_query_parts[0].strip()

        # Build WHERE condition for different search columns
        if search_column in ['fat_id', 'olt', 'fdt_id']:
            # Main table columns
            where_condition = f"LOWER(ut.{search_column}) LIKE LOWER(%s)"
            params = [f"%{search_value}%"]
        elif search_column in ['kota_kab', 'kecamatan', 'kelurahan']:
            # Clusters table columns
            where_condition = f"LOWER(cl.{search_column}) LIKE LOWER(%s)"
            params = [f"%{search_value}%"]
        elif search_column in ['total_hc', 'hc_old', 'hc_icrm']:
            # Home connected table columns
            where_condition = f"LOWER(CAST(hc.{search_column} AS TEXT)) LIKE LOWER(%s)"
            params = [f"%{search_value}%"]
        else:
            # Default to user_terminals table
            where_condition = f"LOWER(CAST(ut.{search_column} AS TEXT)) LIKE LOWER(%s)"
            params = [f"%{search_value}%"]

        # Build final optimized query
        optimized_query = f"""
            {select_and_joins}
            WHERE {where_condition}
            ORDER BY ut.fat_id
            LIMIT 1000
        """

        # Execute query
        data, columns, error = asset_data_service._execute_query(
            optimized_query, tuple(params))

        if error:
            logger.error(f"Error in optimized search: {error}")
            return pd.DataFrame()

        if not data:
            return pd.DataFrame()

        result_df = pd.DataFrame(data, columns=columns)
        logger.info(
            f"Optimized search for {search_column}={search_value} returned {len(result_df)} results")
        return result_df

    except Exception as e:
        logger.error(f"Exception in optimized search: {e}")
        return pd.DataFrame()

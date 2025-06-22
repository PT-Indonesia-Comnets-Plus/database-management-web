from psycopg2 import pool, Error as Psycopg2Error
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import re
import pandas as pd


class AssetPipeline:
    """
    A class to encapsulate the asset data cleaning and preparation pipeline.
    Handles column renaming, capitalization, duplicate removal, missing value filling, type conversions, and data cleaning.
    Finally, splits the processed data into multiple DataFrames corresponding to target database tables.
    """

    def __init__(self):
        """Initializes the pipeline configuration with column settings."""
        # Columns to exclude from string capitalization (if capitalization step is added later)
        self.exclude_columns = {
            "Hostname OLT", "FDT ID", "FATID", "Type OLT", "OLT", "ID FAT",
            "CLEANSING HP", "FAT ID X", "LINK DOKUMEN FEEDER", "LINK DATA ASET", "LINK MAPS"
        }
        # Target column name for duplicate handling during column name cleaning

        self.column_rename_map = {
            "Hostname OLT": "hostname_olt",
            "Kordinat OLT": "koordinat_olt",
            "Brand OLT": "brand_olt",
            "Type OLT": "type_olt",
            "Kapasitas OLT": "kapasitas_olt",
            "Kapasitas port OLT": "kapasitas_port_olt",
            "OLT Port": "olt_port",
            "OLT": "olt",
            "Interface OLT": "interface_olt",
            "Lokasi OLT": "lokasi_olt",
            "FDT ID": "fdt_id",
            "Status OSP AMARTA 1": "status_osp_amarta_fdt",
            "Jumlah Splitter FDT": "jumlah_splitter_fdt",
            "Kapasitas Splitter FDT": "kapasitas_splitter_fdt",
            "FDT New/Existing": "fdt_new_existing",
            "Port FDT": "port_fdt",
            "Koodinat FDT": "koordinat_fdt",
            "FATID": "fat_id",
            "Jumlah Splitter FAT": "jumlah_splitter_fat",
            "Kapasitas Splitter FAT": "kapasitas_splitter_fat",
            "Koodinat FAT": "koordinat_fat",
            "Status OSP AMARTA FAT": "status_osp_amarta_fat",
            "FAT KONDISI": "fat_kondisi",
            "FAT FILTER PEMAKAIAN": "fat_filter_pemakaian",
            "KETERANGAN FULL": "keterangan_full",
            "FAT ID X": "fat_id_x",
            "FILTER FAT CAP": "filter_fat_cap",
            "Cluster": "cluster",
            "Koordinat Cluster": "koordinat_cluster",
            "Area KP": "area_kp",
            "Kota/Kab": "kota_kab",
            "Kecamatan": "kecamatan",
            "Kelurahan": "kelurahan",
            "UP3": "up3",
            "ULP": "ulp",
            "LINK DOKUMEN FEEDER": "link_dokumen_feeder",
            "KETERANGAN DOKUMEN": "keterangan_dokumen",
            "LINK DATA ASET": "link_data_aset",
            "KETERANGAN DATA ASET": "keterangan_data_aset",
            "LINK MAPS": "link_maps",
            "UPDATE ASET": "update_aset",
            "AMARTA UPDATE": "amarta_update",
            "HC OLD": "hc_old",
            "HC iCRM+": "hc_icrm",
            "TOTAL HC": "total_hc",
            "CLEANSING HP": "cleansing_hp",
            "PA": "pa",
            "Tanggal RFS": "tanggal_rfs",
            "Mitra": "mitra",
            "Kategori": "kategori",
            "Sumber Datek": "sumber_datek"
        }

        self.astype_map = {
            "kapasitas_olt": "Int64",
            "kapasitas_port_olt": "Int64",
            "olt_port": "Int64",
            "jumlah_splitter_fdt": "Int64",
            "kapasitas_splitter_fdt": "Int64",
            "port_fdt": "Int64",
            "jumlah_splitter_fat": "Int64",
            "kapasitas_splitter_fat": "Int64",
            "hc_old": "Int64",
            "hc_icrm": "Int64",
            "total_hc": "Int64",
            "tanggal_rfs": "datetime64[ns]"
        }

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renames columns based on predefined mappings."""
        print("  Pipeline Step: Renaming columns...")
        return df.rename(columns=self.column_rename_map, errors="ignore") if not df.empty else df

    @staticmethod
    def fill_na_values(df: pd.DataFrame) -> pd.DataFrame:
        """Fills missing values with default values for numerical columns."""
        if df.empty:
            print("  Pipeline Step: Skipping NA fill (empty DataFrame).")
            return df

        default_fill = {
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
        }

        print("  Pipeline Step: Filling NA values...")
        df.fillna(default_fill, inplace=True)
        return df

    # --- Moved inside the class ---
    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans column names: strip, remove extra spaces, handle 'Status OSP AMARTA' duplicates."""
        if df.empty:
            return df
        print("  Pipeline Step: Cleaning column names...")

        target_col_name = "Status OSP AMARTA"  # Assuming this is still relevant
        new_cols = []
        count = 1

        for col in df.columns:
            current_col_name = col
            if col == target_col_name:
                current_col_name = f"{target_col_name} {count}"
                count += 1
            cleaned_name = re.sub(r"\s+", " ", str(current_col_name)).strip()
            new_cols.append(cleaned_name)

        df.columns = new_cols
        return df

    def capitalize_columns_except(self, df: pd.DataFrame) -> pd.DataFrame:
        """Capitalizes string columns except those specified in `exclude_columns`."""
        if df.empty:
            return df
        print("  Pipeline Step: Capitalizing string values...")
        for col in df.columns:
            if col not in self.exclude_columns and df[col].dtype == "object":
                df[col] = df[col].apply(
                    lambda x: x.title().strip() if isinstance(x, str) else x)
        return df
    # -----------------------------

    def clean_column_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans specific known problematic values in columns."""
        print("  Pipeline Step: Cleaning specific column values (e.g., tanggal_rfs)...")
        if "tanggal_rfs" in df.columns:
            df["tanggal_rfs"] = df["tanggal_rfs"].astype(
                str).str.replace("0203", "2023", regex=False)
        return df

    def _convert_column_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converts column types based on predefined mappings."""
        if df.empty:
            return df

        int64_cols = [col for col, dtype in self.astype_map.items()
                      if dtype == "Int64"]
        other_cols = {col: dtype for col,
                      dtype in self.astype_map.items() if dtype != "Int64"}

        print("  Pipeline Step: Converting column types (Int64)...")
        for col in int64_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(
                    "[., ]", "", regex=True).str.strip()
                df[col] = pd.to_numeric(
                    df[col], errors="coerce").astype("Int64")

        print("  Pipeline Step: Converting column types (Others)...")
        df = df.astype(other_cols, errors="ignore")
        return df

    # --- Coordinate Cleaning Methods ---

    def _clean_comma_separated(self, coord: Any) -> Optional[str]:
        """Handles standard 'lat,lon', standardizes decimal, removes consecutive dots."""
        if pd.isna(coord):
            return None
        coord_str = str(coord).strip()
        if ',' not in coord_str:
            return None

        parts = [part.strip() for part in coord_str.split(',', 1)]
        if len(parts) == 2:
            lat_part = parts[0].replace(',', '.')
            lon_part = parts[1].replace(',', '.')
            lat_part = re.sub(r'\.+', '.', lat_part).strip('.')
            lon_part = re.sub(r'\.+', '.', lon_part).strip('.')
            try:
                float(lat_part)
                float(lon_part)
                return f"{lat_part},{lon_part}"
            except ValueError:
                return None
        return None

    def _clean_degree_as_separator(self, coord: Any) -> Optional[str]:
        """Handles coordinates separated by '°'."""
        if pd.isna(coord):
            return None
        coord_str = str(coord)

        if '°' not in coord_str:
            return None

        try:
            parts = coord_str.split('°')
            if len(parts) >= 2:
                lat_part = parts[0].strip()
                lon_part = ''.join(parts[1:]).strip()
                return self._clean_comma_separated(f"{lat_part},{lon_part}")
        except Exception:
            pass
        return None

    def _clean_two_commas_with_space(self, coord: Any) -> Optional[str]:
        """Handles formats like 'lat, lon' or 'lat  lon' by replacing separators with a single comma."""
        if pd.isna(coord):
            return None
        coord_str = str(coord).strip()
        # Replace space-comma or multiple spaces with a single comma
        coord_str_standardized = coord_str.replace(', ', ',').replace(' ', ',')
        return self._clean_comma_separated(coord_str_standardized)

    def _clean_dot_space_separated(self, coord: Any) -> Optional[str]:
        """Handles format like '-7.90845. 113.35127' -> '-7.90845,113.35127'."""
        if pd.isna(coord):
            return None
        coord_str = str(coord).strip()
        if not coord_str:
            return None
        # Regex to match number, dot, space(s), number
        match = re.match(r'^(-?\d+\.?\d*)\.\s+(-?\d+\.?\d*)$', coord_str)
        if match:
            lat_part = match.group(1)
            lon_part = match.group(2)
            return f"{lat_part},{lon_part}"  # Already clean format
        return None

    def _clean_with_e_separator(self, coord: Any) -> Optional[str]:
        """Handles coordinates separated by 'E', potentially with 'S' prefix and scaling."""
        if pd.isna(coord):
            return None
        coord_str = str(coord).strip()
        if 'E' not in coord_str.upper():
            return None  # Case-insensitive check
        try:
            parts = re.split('E', coord_str, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                lat_part = parts[0].strip()
                lon_part = parts[1].strip()
                is_south = False
                if lat_part.upper().startswith('S'):
                    is_south = True
                    lat_part = lat_part[1:].strip()  # Remove 'S'

                lat_float = float(lat_part)
                lon_float = float(lon_part)

                # Apply scaling logic (adjust thresholds if needed)
                lat_final = lat_float / \
                    100 if abs(lat_float) > 90 else lat_float
                lon_final = lon_float / \
                    100 if abs(lon_float) > 180 else lon_float

                if is_south:
                    lat_final = -abs(lat_final)  # Ensure negative for South

                return f"{lat_final},{lon_final}"
        except (ValueError, TypeError, IndexError):
            pass  # Ignore conversion/split errors
        return None

    def _clean_dot_separated_no_comma(self, coord: Any) -> Optional[str]:
        """Handles formats like 'X.Y.A.B' -> 'X.Y,A.B' where dot acts as separator."""
        if pd.isna(coord):
            return None
        coord_str = str(coord).strip()
        if ',' in coord_str:
            return None  # Skip if already has comma

        # Try matching pattern like -7.12345.112.67890
        match_simple_dot_sep = re.match(
            r'^(-?\d+\.\d+)\.(\d+\.?\d*)$', coord_str)
        if match_simple_dot_sep:
            lat_part = match_simple_dot_sep.group(1)
            lon_part = match_simple_dot_sep.group(2)
            # Pass through standard comma cleaner for final validation
            return self._clean_comma_separated(f"{lat_part},{lon_part}")
        return None

    def _clean_merged_coordinates(self, coord: Any) -> Optional[str]:
        """Handles specific merged formats like '-7362714112732918' -> '-7.362714,112.732918'."""
        if pd.isna(coord):
            return None
        coord_str = str(coord).strip().replace(" ", "").replace(",", "")

        # Example pattern: -7 followed by 6 digits, then 112 followed by 6 digits
        match_specific_merged = re.match(
            r'^(-?\d)(\d{6})(\d{3})(\d{6})$', coord_str)
        if match_specific_merged:
            lat_sign = match_specific_merged.group(1)
            lat_dec = match_specific_merged.group(2)
            lon_int = match_specific_merged.group(3)
            lon_dec = match_specific_merged.group(4)
            lat = f"{lat_sign}.{lat_dec}"
            lon = f"{lon_int}.{lon_dec}"
            return f"{lat},{lon}"
        return None

    def _clean_split_from_long_float(self, coord: Any) -> Optional[str]:
        """Handles large raw float/int numbers by splitting them based on assumed digit counts."""
        try:
            if not isinstance(coord, (float, int)) or pd.isna(coord):
                return None

            # Format, remove sign and decimal for splitting, keep original sign
            coord_sign = "-" if coord < 0 else ""
            coord_str_raw = "{:.10f}".format(abs(coord)).replace(
                '.', '')  # Use absolute value
            coord_str = coord_str_raw.rstrip('0')

            # Heuristic: Check if length suggests a merged lat/lon
            if len(coord_str) < 10:
                return None  # Too short

            # Example split logic (adjust indices based on typical data)
            # Assumes: 1 digit int lat, 6 digits dec lat, 3 digits int lon, rest dec lon
            lat_int_digit = coord_str[0]
            lat_dec_digits = coord_str[1:7]
            lon_int_digits = coord_str[7:10]
            lon_dec_digits = coord_str[10:]

            lat = f"{coord_sign}{lat_int_digit}.{lat_dec_digits}"
            lon = f"{lon_int_digits}.{lon_dec_digits}"

            # Validate and return using the standard comma cleaner
            return self._clean_comma_separated(f"{lat},{lon}")

        except (IndexError, ValueError, TypeError):
            pass  # Ignore errors during splitting/conversion
        return None

    def _apply_coordinate_cleaning(self, coord: Any) -> Optional[str]:
        """Applies various cleaning functions in order of precedence."""
        if pd.isna(coord):
            return None

        # Try cleaning float first if applicable
        cleaned = self._clean_split_from_long_float(coord)
        if cleaned:
            return cleaned

        # Process as string
        coord_str_raw = str(coord)
        # Basic cleanup of common problematic characters
        coord_str = coord_str_raw.replace(
            'Â', '').replace('\u00A0', ' ').strip()

        if not coord_str or coord_str.lower() in ['none', 'nan', '<na>']:
            return None

        # Apply string-based cleaners in order
        cleaned = (
            self._clean_degree_as_separator(coord_str) or
            self._clean_two_commas_with_space(coord_str) or
            self._clean_dot_space_separated(coord_str) or
            self._clean_with_e_separator(coord_str) or
            self._clean_dot_separated_no_comma(coord_str) or
            self._clean_merged_coordinates(coord_str)
            # Add other specific cleaners here if needed
        )
        if cleaned:
            return cleaned

        # Final attempt with the standard comma separator cleaner
        if ',' in coord_str:
            return self._clean_comma_separated(coord_str)

        return None  # Return None if no method could clean it

    def _clean_invalid_characters(self, value: Any) -> Optional[str]:
        """Removes characters not allowed in numeric coordinates (digits, dot, comma, minus)."""
        if pd.isna(value):
            return None
        try:
            # Keep only digits, dot, comma, minus sign
            cleaned = re.sub(r'[^\d\.,-]', '', str(value))
            return cleaned if cleaned else None  # Return None if empty after cleaning
        except Exception:
            return None

    def _process_coordinate_column(self, df: pd.DataFrame, base_name: str) -> pd.DataFrame:
        """Cleans, splits, and converts a single coordinate column (e.g., 'koordinat_olt')."""
        original_col = f"koordinat_{base_name}"
        lat_col = f"latitude_{base_name}"
        lon_col = f"longitude_{base_name}"

        if original_col not in df.columns:
            print(
                f"  -> Column '{original_col}' not found. Skipping processing.")
            # Ensure target columns exist even if source is missing
            if lat_col not in df.columns:
                df[lat_col] = np.nan
            if lon_col not in df.columns:
                df[lon_col] = np.nan
            return df

        print(f"  -> Processing column '{original_col}'...")
        # Apply the cleaning chain
        cleaned_coords = df[original_col].apply(
            self._apply_coordinate_cleaning)

        # Split into temporary lat/lon series
        split_data = cleaned_coords.str.split(',', expand=True, n=1)

        # Assign to final columns, cleaning invalid chars and converting
        temp_lat = split_data[0] if split_data.shape[1] > 0 else pd.Series([
                                                                           np.nan] * len(df))
        temp_lon = split_data[1] if split_data.shape[1] > 1 else pd.Series([
                                                                           np.nan] * len(df))

        df[lat_col] = temp_lat.apply(self._clean_invalid_characters)
        df[lon_col] = temp_lon.apply(self._clean_invalid_characters)

        df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
        df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')

        print(
            f"     ✅ Split into '{lat_col}' and '{lon_col}', converted to numeric.")

        # Drop the original coordinate column after processing
        df.drop(columns=[original_col], inplace=True, errors='ignore')
        print(f"     ✅ Dropped original column '{original_col}'.")

        return df

    def _process_all_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processes all standard coordinate columns (OLT, FDT, FAT, Cluster)."""
        print("\n--- Processing Coordinate Columns ---")
        coordinate_bases = ["olt", "fdt", "fat", "cluster"]
        for base in coordinate_bases:
            df = self._process_coordinate_column(df, base)
        print("✅ Coordinate processing finished.")
        return df

    # --- Data Splitting Methods ---

    def _clean_fat_id(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans the 'fat_id' column: strip, uppercase, remove whitespace/hyphens."""
        # This is part of split_data, logging done there
        if 'fat_id' in df.columns:
            df['fat_id'] = (
                df['fat_id']
                .astype(str)
                .str.strip()
                .str.upper()
                # Remove whitespace, tabs, hyphens
                .str.replace(r'[\s\t\-]+', '', regex=True)
            )
        return df

    def _expand_fat_id_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        """Expands rows where 'fat_id' represents a range (e.g., 'ID1-ID2') into separate rows."""
        # This is part of split_data, logging done there
        if 'fat_id' not in df.columns:
            return df

        expanded_rows = []
        for _, row in df.iterrows():
            fat_id = str(row['fat_id']).strip(
            ) if pd.notna(row['fat_id']) else ''

            # Check for range format (contains '-')
            if '-' in fat_id:
                id_parts = [part.strip()
                            for part in fat_id.split('-') if part.strip()]
                # If it's a valid range (exactly two parts after split)
                if len(id_parts) == 2:
                    row1 = row.copy()
                    row1['fat_id'] = id_parts[0]
                    expanded_rows.append(row1)

                    row2 = row.copy()
                    row2['fat_id'] = id_parts[1]
                    expanded_rows.append(row2)
                else:
                    # Invalid range format, keep original row
                    expanded_rows.append(row)
            else:
                # Not a range, keep original row
                expanded_rows.append(row)

        return pd.DataFrame(expanded_rows) if expanded_rows else pd.DataFrame(columns=df.columns)

    def split_data(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Splits the processed DataFrame into multiple DataFrames based on target table schemas."""
        print("\n--- Splitting Data for Target Tables ---")
        if df.empty:
            print("  -> Input DataFrame is empty. Returning empty dictionary.")
            print("  Pipeline Step: Skipping data splitting (empty DataFrame).")
            return {}

        # Clean and expand fat_id before splitting
        df = self._clean_fat_id(df)
        df = self._expand_fat_id_ranges(df)
        df.drop_duplicates(subset='fat_id', keep="first",
                           inplace=True)  # Keep cleaning fat_id here
        print(
            f"  -> Base data prepared with {len(df)} unique FAT IDs after cleaning/expansion.")

        split_dfs = {}
        table_definitions = {
            "user_terminals": [
                "hostname_olt", "latitude_olt", "longitude_olt", "brand_olt", "type_olt",
                "kapasitas_olt", "kapasitas_port_olt", "olt_port", "olt", "interface_olt",
                "fdt_id", "status_osp_amarta_fdt", "jumlah_splitter_fdt", "kapasitas_splitter_fdt",
                "fdt_new_existing", "port_fdt", "latitude_fdt", "longitude_fdt",
                "fat_id", "jumlah_splitter_fat", "kapasitas_splitter_fat", "latitude_fat", "longitude_fat",
                "status_osp_amarta_fat", "fat_kondisi", "fat_filter_pemakaian", "keterangan_full",
                "fat_id_x", "filter_fat_cap"
            ],
            "clusters": ["latitude_cluster", "longitude_cluster", "area_kp", "kota_kab", "kecamatan", "kelurahan", "up3", "ulp", "fat_id"],
            "home_connecteds": ["hc_old", "hc_icrm", "total_hc", "cleansing_hp", "fat_id"],
            "dokumentasis": ["status_osp_amarta_fat", "link_dokumen_feeder", "keterangan_dokumen", "link_data_aset", "keterangan_data_aset", "link_maps", "update_aset", "amarta_update", "fat_id"],
            "additional_informations": ["pa", "tanggal_rfs", "mitra", "kategori", "sumber_datek", "fat_id"]
        }

        for table_name, columns in table_definitions.items():
            # Select only columns that exist in the DataFrame AND are defined for the table
            available_cols = [col for col in columns if col in df.columns]
            if 'fat_id' not in available_cols and 'fat_id' in df.columns:
                # Ensure fat_id is always included if available
                available_cols.append('fat_id')

            if not available_cols:
                print(
                    f"  -> No columns available for table '{table_name}'. Skipping.")
                split_dfs[table_name] = pd.DataFrame()
                continue

            split_df = df[available_cols].copy()
            # No need to clean fat_id again as it was done on the base df
            split_dfs[table_name] = split_df
            print(
                f"  ✅ Split data for '{table_name}' ({len(split_df)} rows, {len(available_cols)} columns).")

        print("✅ Data splitting finished.")
        return split_dfs

    # --- Main Pipeline Execution ---

    def run(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Runs the complete asset data cleaning and processing pipeline,
        returning a single processed DataFrame before splitting.

        Args:
            df: The raw input pandas DataFrame.

        Returns:
            A single processed pandas DataFrame containing all cleaned data,
            Returns None if a critical error occurs during processing.
        """
        if df.empty:
            print("Input DataFrame is empty. Skipping pipeline.")
            return {}  # Return empty dict for empty input

        try:
            print("Starting Asset Pipeline...")
            df = self.clean_column_names(df)  # Step 1 <-- Now called correctly
            df = self.capitalize_columns_except(df)  # Step 2
            df = self._rename_columns(df)  # Step 3
            df = self.fill_na_values(df)  # Step 4
            df = self.clean_column_values(df)  # Step 5
            df = self._process_all_coordinates(
                df)  # Step 6: Process coordinates
            # Step 7: Convert types AFTER coordinates are split
            df = self._convert_column_types(df)

            # Step 8: Split the processed data
            split_dataframes = self.split_data(df)
            print("Asset Pipeline finished successfully (before splitting).")
            return df
        except Exception as e:
            print(f"ERROR during pipeline execution: {e}")
            # st.error(...) removed, error logged above
            return None  # Return None on critical pipeline error

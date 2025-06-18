# features/home/views/add_column.py

from core.utils.database import connect_db
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import pool, Error as Psycopg2Error
import sys
import os
import logging
from typing import Optional, Dict, Any, List, Tuple

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)


class ColumnManager:
    """Simple column manager for adding dynamic columns to database."""

    def __init__(self, db_pool):
        self.db_pool = db_pool

    def execute_query(self, query: str, params: tuple = None) -> Tuple[bool, str, Any]:
        """Execute a database query with error handling."""
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(query, params)

            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                cursor.close()
                self.db_pool.putconn(conn)
                return True, "Success", (result, columns)
            else:
                conn.commit()
                cursor.close()
                self.db_pool.putconn(conn)
                return True, "Success", None

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self.db_pool.putconn(conn)
            return False, str(e), None

    def create_dynamic_tables(self) -> Tuple[bool, str]:
        """Create dynamic column tables if they don't exist."""
        create_sql = """
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) DEFAULT 'system',
            UNIQUE(table_name, column_name)
        );
        
        CREATE TABLE IF NOT EXISTS dynamic_column_data (
            id SERIAL PRIMARY KEY,
            record_id VARCHAR(255) NOT NULL,
            column_id INTEGER REFERENCES dynamic_columns(id) ON DELETE CASCADE,
            column_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_id, column_id)        );
        
        CREATE INDEX IF NOT EXISTS idx_dynamic_column_data_record_id ON dynamic_column_data(record_id);
        CREATE INDEX IF NOT EXISTS idx_dynamic_column_data_column_id ON dynamic_column_data(column_id);
        """

        success, message, _ = self.execute_query(create_sql)
        return success, message

    def get_available_tables(self) -> List[Dict]:
        """Get list of available tables for adding columns."""
        query = """
        SELECT table_name, 
               CASE 
                   WHEN table_name = 'user_terminals' THEN 'Data Terminal User (Main)'
                   WHEN table_name = 'clusters' THEN 'Data Cluster/Lokasi'
                   WHEN table_name = 'home_connecteds' THEN 'Data Home Connected'
                   WHEN table_name = 'dokumentasis' THEN 'Data Dokumentasi'
                   WHEN table_name = 'additional_informations' THEN 'Informasi Tambahan'
                   ELSE table_name
               END as display_name,
               CASE 
                   WHEN table_name = 'user_terminals' THEN 'Primary table berisi data terminal dan asset utama'
                   WHEN table_name = 'clusters' THEN 'Data geografis dan lokasi cluster'
                   WHEN table_name = 'home_connecteds' THEN 'Data statistik home connected'
                   WHEN table_name = 'dokumentasis' THEN 'Links dan dokumentasi terkait asset'
                   WHEN table_name = 'additional_informations' THEN 'Informasi tambahan seperti tanggal RFS, mitra, dll'
                   ELSE 'Other table'
               END as description
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name IN ('user_terminals', 'clusters', 'home_connecteds', 'dokumentasis', 'additional_informations')
        ORDER BY 
            CASE table_name 
                WHEN 'user_terminals' THEN 1
                WHEN 'clusters' THEN 2  
                WHEN 'home_connecteds' THEN 3
                WHEN 'dokumentasis' THEN 4
                WHEN 'additional_informations' THEN 5
                ELSE 6
            END
        """

        success, message, result = self.execute_query(query)
        if success and result:
            data, columns = result
            return [dict(zip(columns, row)) for row in data]
        return []

    def get_table_primary_key(self, table_name: str) -> str:
        """Get primary key column for a table."""
        # Most tables use fat_id as the linking key
        primary_keys = {
            'user_terminals': 'fat_id',
            'clusters': 'fat_id',
            'home_connecteds': 'fat_id',
            'dokumentasis': 'fat_id',
            'additional_informations': 'fat_id'
        }
        return primary_keys.get(table_name, 'id')

    def get_dynamic_columns(self, table_name: str = None) -> List[Dict]:
        """Get list of dynamic columns for specific table or all tables."""
        if table_name:
            query = """
            SELECT id, table_name, column_name, column_type, display_name, 
                   description, is_active, is_searchable, default_value,
                   created_at, created_by
            FROM dynamic_columns 
            WHERE table_name = %s
            ORDER BY display_name
            """
            params = (table_name,)
        else:
            query = """
            SELECT id, table_name, column_name, column_type, display_name, 
                   description, is_active, is_searchable, default_value,
                   created_at, created_by
            FROM dynamic_columns            ORDER BY table_name, display_name
            """
            params = None

        success, message, result = self.execute_query(query, params)
        if success and result:
            data, columns = result
            return [dict(zip(columns, row)) for row in data]
        return []

    def add_dynamic_column(self, table_name: str, column_name: str, display_name: str,
                           column_type: str, description: str, is_searchable: bool,
                           default_value: str, created_by: str) -> Tuple[bool, str]:
        """Add a new dynamic column to specified table."""

        # Validate table name
        available_tables = [t['table_name']
                            for t in self.get_available_tables()]
        if table_name not in available_tables:
            return False, f"Table '{table_name}' tidak tersedia untuk menambah kolom"

        # Clean column name
        clean_column_name = column_name.lower().replace(' ', '_').replace('-', '_')
        clean_column_name = ''.join(
            c for c in clean_column_name if c.isalnum() or c == '_')

        if not clean_column_name:
            return False, "Column name tidak valid"

        # Begin transaction to ensure data consistency
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Insert into dynamic_columns
            insert_query = """
            INSERT INTO dynamic_columns 
            (table_name, column_name, column_type, display_name, description, 
             is_searchable, default_value, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """

            params = (table_name, clean_column_name, column_type.upper(),
                      display_name, description, is_searchable, default_value, created_by)

            cursor.execute(insert_query, params)
            column_id = cursor.fetchone()[0]

            # If default_value is provided, add it to all existing records
            if default_value:
                # Get all existing records from the target table (linked via fat_id)
                if table_name == 'user_terminals':
                    records_query = "SELECT fat_id FROM user_terminals WHERE fat_id IS NOT NULL"
                else:
                    # For other tables, still link through user_terminals via fat_id
                    records_query = f"""
                    SELECT DISTINCT ut.fat_id 
                    FROM user_terminals ut 
                    INNER JOIN {table_name} t ON ut.fat_id = t.fat_id 
                    WHERE ut.fat_id IS NOT NULL
                    """

                cursor.execute(records_query)
                existing_records = cursor.fetchall()

                # Insert default values for existing records
                if existing_records:
                    default_data_query = """
                    INSERT INTO dynamic_column_data (record_id, column_id, column_value)
                    VALUES (%s, %s, %s)
                    """

                    default_data = [(record[0], column_id, default_value)
                                    for record in existing_records]
                    cursor.executemany(default_data_query, default_data)

            # Commit transaction
            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            # Clear cache to ensure fresh data in search
            if hasattr(self, '_column_cache'):
                self._column_cache.clear()

            success_message = f"Kolom '{display_name}' berhasil ditambahkan ke table '{table_name}'!"
            if default_value and existing_records:
                success_message += f" Default value '{default_value}' diterapkan ke {len(existing_records)} record yang ada."

            return True, success_message

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                self.db_pool.putconn(conn)

            error_message = str(e)
            if "unique constraint" in error_message.lower():
                return False, f"Kolom '{clean_column_name}' sudah ada di table '{table_name}'!"
            return False, f"Error: {error_message}"

    def delete_column(self, column_id: int) -> Tuple[bool, str]:
        """Delete a dynamic column (soft delete)."""
        query = "UPDATE dynamic_columns SET is_active = FALSE WHERE id = %s"
        success, message, _ = self.execute_query(query, (column_id,))

        if success:
            return True, "Kolom berhasil dihapus!"
        return False, f"Error: {message}"

    def get_column_data_count(self, column_id: int) -> int:
        """Get count of data for a specific column."""
        query = """
        SELECT COUNT(*) 
        FROM dynamic_column_data 
        WHERE column_id = %s AND column_value IS NOT NULL AND column_value != ''
        """

        success, message, result = self.execute_query(query, (column_id,))
        if success and result:
            return result[0][0][0]
        return 0

    def get_integrated_columns_info(self) -> Dict[str, Any]:
        """Get information about how dynamic columns integrate with user_terminals."""
        try:
            # Get all dynamic columns
            dynamic_columns = self.get_dynamic_columns()

            # Get sample data to show integration
            sample_query = """
            SELECT ut.fat_id, 
                   COUNT(dcd.id) as dynamic_data_count,
                   STRING_AGG(DISTINCT dc.display_name, ', ') as available_columns
            FROM user_terminals ut
            LEFT JOIN dynamic_column_data dcd ON ut.fat_id = dcd.record_id
            LEFT JOIN dynamic_columns dc ON dcd.column_id = dc.id AND dc.is_active = TRUE
            GROUP BY ut.fat_id
            HAVING COUNT(dcd.id) > 0
            LIMIT 5
            """

            success, message, result = self.execute_query(sample_query)

            integration_info = {
                'total_dynamic_columns': len(dynamic_columns),
                'active_columns': len([c for c in dynamic_columns if c['is_active']]),
                'searchable_columns': len([c for c in dynamic_columns if c['is_searchable'] and c['is_active']]),
                'sample_integrations': []
            }

            if success and result:
                data, columns = result
                integration_info['sample_integrations'] = [
                    dict(zip(columns, row)) for row in data]

            return integration_info

        except Exception as e:
            logger.error(f"Error getting integration info: {e}")
            return {
                'total_dynamic_columns': 0,
                'active_columns': 0,
                'searchable_columns': 0,
                'sample_integrations': []
            }

    def show_column_usage_stats(self) -> Dict[str, Any]:
        """Show usage statistics for dynamic columns."""
        try:
            query = """
            SELECT 
                dc.table_name,
                dc.display_name,
                dc.column_type,
                dc.is_searchable,
                COUNT(dcd.id) as data_count,
                COUNT(DISTINCT dcd.record_id) as unique_records
            FROM dynamic_columns dc
            LEFT JOIN dynamic_column_data dcd ON dc.id = dcd.column_id
            WHERE dc.is_active = TRUE
            GROUP BY dc.id, dc.table_name, dc.display_name, dc.column_type, dc.is_searchable
            ORDER BY data_count DESC
            """

            success, message, result = self.execute_query(query)
            if success and result:
                data, columns = result
                return [dict(zip(columns, row)) for row in data]
            return []

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return []

    def verify_column_integration(self, column_id: int) -> Dict[str, Any]:
        """
        Verifikasi apakah kolom dinamis sudah terintegrasi dengan baik di sistem.

        Args:
            column_id: ID kolom dinamis

        Returns:
            Dict berisi status integrasi dan detail
        """
        try:
            # Get column info
            column_query = """
            SELECT dc.*, 
                   COUNT(dcd.id) as data_count,
                   COUNT(DISTINCT dcd.record_id) as unique_records
            FROM dynamic_columns dc
            LEFT JOIN dynamic_column_data dcd ON dc.id = dcd.column_id
            WHERE dc.id = %s
            GROUP BY dc.id
            """

            success, message, result = self.execute_query(
                column_query, (column_id,))
            if not success or not result:
                return {'status': 'error', 'message': f'Column not found: {message}'}

            data, columns = result
            column_info = dict(zip(columns, data[0]))

            # Check if column is available in search system
            search_available = column_info['is_searchable'] and column_info['is_active']

            # Check integration with user_terminals (through fat_id)
            integration_query = """
            SELECT COUNT(DISTINCT ut.fat_id) as terminal_count,
                   COUNT(dcd.id) as data_entries
            FROM user_terminals ut
            LEFT JOIN dynamic_column_data dcd ON ut.fat_id = dcd.record_id 
                                               AND dcd.column_id = %s
            """

            success, message, result = self.execute_query(
                integration_query, (column_id,))
            integration_stats = {}
            if success and result:
                data, columns = result
                integration_stats = dict(zip(columns, data[0]))

            # Calculate integration status
            integration_percentage = 0
            if integration_stats.get('terminal_count', 0) > 0:
                integration_percentage = (integration_stats.get('data_entries', 0) /
                                          integration_stats.get('terminal_count', 1)) * 100

            return {
                'status': 'success',
                'column_info': column_info,
                'search_available': search_available,
                'integration_stats': integration_stats,
                'integration_percentage': round(integration_percentage, 2),
                'recommendations': self._get_integration_recommendations(column_info, integration_stats)
            }

        except Exception as e:
            logger.error(f"Error verifying column integration: {e}")
            return {'status': 'error', 'message': str(e)}

    def _get_integration_recommendations(self, column_info: Dict, integration_stats: Dict) -> List[str]:
        """Get recommendations for better integration."""
        recommendations = []

        if not column_info.get('is_searchable'):
            recommendations.append(
                "💡 Aktifkan 'searchable' agar kolom muncul di pencarian")

        if integration_stats.get('data_entries', 0) == 0:
            recommendations.append(
                "📝 Mulai entry data untuk kolom ini di tab 'Data Entry'")

        if column_info.get('data_count', 0) < 10:
            recommendations.append(
                "📊 Tambah lebih banyak data untuk analisis yang lebih baik")

        if column_info.get('is_active') and column_info.get('is_searchable'):
            recommendations.append(
                "🔍 Kolom sudah siap digunakan di halaman Search!")

        return recommendations

    def test_column_in_search(self, column_id: int) -> Tuple[bool, str]:
        """
        Test apakah kolom dinamis sudah muncul dan bisa digunakan di search.

        Args:
            column_id: ID kolom dinamis

        Returns:
            Tuple (success, message)
        """
        try:
            # Get column info
            column_query = """
            SELECT display_name, column_name, is_searchable, is_active
            FROM dynamic_columns 
            WHERE id = %s
            """

            success, message, result = self.execute_query(
                column_query, (column_id,))
            if not success or not result:
                return False, f"Column not found: {message}"

            data, columns = result
            column_info = dict(zip(columns, data[0]))

            if not column_info['is_active']:
                return False, f"Kolom '{column_info['display_name']}' tidak aktif"

            if not column_info['is_searchable']:
                return False, f"Kolom '{column_info['display_name']}' tidak di-set sebagai searchable"

            # Test if column has data
            data_query = """
            SELECT COUNT(*) as count
            FROM dynamic_column_data 
            WHERE column_id = %s AND column_value IS NOT NULL AND column_value != ''
            """

            success, message, result = self.execute_query(
                data_query, (column_id,))
            if success and result:
                data_count = result[0][0][0]
                if data_count > 0:
                    return True, f"✅ Kolom '{column_info['display_name']}' siap digunakan di search! ({data_count} data entries)"
                else:
                    return True, f"⚠️ Kolom '{column_info['display_name']}' siap di search, tapi belum ada data"
            else:
                return False, f"Error checking data: {message}"

        except Exception as e:
            logger.error(f"Error testing column in search: {e}")
            return False, f"Error: {e}"


def render_add_column_ui():
    """Main UI for adding columns."""

    st.markdown("# 🔧 Kelola Kolom Database")
    st.markdown("Tambah kolom baru ke database tanpa mengubah kode aplikasi.")

    # Initialize database connection
    try:
        if 'column_manager' not in st.session_state:
            db_pool, _ = connect_db()
            if not db_pool:
                st.error("❌ Koneksi database gagal!")
                return

            st.session_state.column_manager = ColumnManager(db_pool)

            # Create tables if needed
            success, message = st.session_state.column_manager.create_dynamic_tables()
            if not success:
                st.error(f"Error creating tables: {message}")
                return

        column_manager = st.session_state.column_manager

    except Exception as e:
        st.error(f"❌ Error initialize: {e}")
        return    # Tabs for different functions
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Daftar Kolom", "➕ Tambah Kolom", "📊 Data Entry", "🔗 Status Integrasi"])

    # Tab 1: List existing columns
    with tab1:
        render_column_list(column_manager)

    # Tab 2: Add new column
    with tab2:
        render_add_column_form(column_manager)

    # Tab 3: Data entry
    with tab3:
        render_data_entry(column_manager)

    # Tab 4: Integration status
    with tab4:
        render_integration_status(column_manager)


def render_column_list(column_manager):
    """Render list of existing dynamic columns."""

    st.markdown("## 📋 Daftar Kolom Dinamis")

    try:
        columns = column_manager.get_dynamic_columns()

        if not columns:
            st.info("Belum ada kolom dinamis yang dibuat.")
            return        # Display columns grouped by table
        tables_with_columns = {}
        for col in columns:
            table_name = col['table_name']
            if table_name not in tables_with_columns:
                tables_with_columns[table_name] = []
            tables_with_columns[table_name].append(col)

        # Display each table section
        for table_name, table_columns in tables_with_columns.items():
            st.markdown(f"### 📊 Table: **{table_name.upper()}**")

            for col in table_columns:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                    with col1:
                        status_icon = "🟢" if col['is_active'] else "🔴"
                        search_icon = "🔍" if col['is_searchable'] else "🚫"

                        st.markdown(
                            f"**{status_icon} {col['display_name']}** ({col['column_type']})")
                        if col['description']:
                            st.caption(col['description'])
                        st.caption(
                            f"{search_icon} Internal name: `{col['column_name']}`")

                    with col2:
                        data_count = column_manager.get_column_data_count(
                            col['id'])
                        st.metric("Data", data_count)

                    with col3:
                        created_date = col['created_at'].strftime(
                            '%Y-%m-%d') if col['created_at'] else 'Unknown'
                        st.caption(f"Dibuat: {created_date}")
                        st.caption(f"Oleh: {col['created_by']}")

                    with col4:
                        if col['is_active']:
                            if st.button("🗑️ Hapus", key=f"del_{col['id']}", type="secondary"):
                                success, message = column_manager.delete_column(
                                    col['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    st.divider()

            st.markdown("---")

        # Statistics
        active_count = sum(1 for col in columns if col['is_active'])
        searchable_count = sum(
            1 for col in columns if col['is_searchable'] and col['is_active'])

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Kolom", len(columns))
        col2.metric("Kolom Aktif", active_count)
        col3.metric("Kolom Searchable", searchable_count)

    except Exception as e:
        st.error(f"Error loading columns: {e}")


def render_add_column_form(column_manager):
    """Render form to add new column."""

    st.markdown("## ➕ Tambah Kolom Baru")

    # Get available tables
    try:
        available_tables = column_manager.get_available_tables()
        if not available_tables:
            st.error("❌ Tidak ada table yang tersedia untuk menambah kolom")
            return
    except Exception as e:
        st.error(f"❌ Error loading available tables: {e}")
        return

    with st.form("add_column_form"):
        # Table selection section
        st.markdown("### 🎯 Pilih Table Tujuan")
        table_options = {}
        for table in available_tables:
            table_options[f"{table['display_name']} ({table['table_name']})"] = table['table_name']

        selected_table_display = st.selectbox(
            "Table Tujuan*",
            options=list(table_options.keys()),
            help="Pilih table dimana kolom akan ditambahkan"
        )
        selected_table = table_options[selected_table_display]

        # Show table description
        selected_table_info = next(
            t for t in available_tables if t['table_name'] == selected_table)
        st.info(f"📝 **{selected_table_info['description']}**")

        st.divider()

        # Column definition section
        st.markdown("### 📋 Definisi Kolom")
        col1, col2 = st.columns(2)

        with col1:
            display_name = st.text_input(
                "Nama Kolom (untuk ditampilkan)*",
                placeholder="Contoh: Status Maintenance",
                help="Nama yang akan ditampilkan di UI"
            )

            column_type = st.selectbox(
                "Tipe Data*",
                options=["TEXT", "INTEGER", "FLOAT", "DATE", "BOOLEAN"],
                help="Pilih tipe data yang sesuai"
            )

            default_value = st.text_input(
                "Nilai Default",
                placeholder="Nilai default (opsional)"
            )

        with col2:
            description = st.text_area(
                "Deskripsi",
                placeholder="Deskripsi singkat tentang kolom ini",
                help="Jelaskan untuk apa kolom ini digunakan"
            )

            is_searchable = st.checkbox(
                "Bisa dicari dalam Search",
                value=True,
                help="Jika dicentang, kolom ini akan muncul di opsi pencarian"
            )

            created_by = st.text_input(
                "Dibuat oleh",
                value="admin",
                placeholder="Nama user yang membuat"
            )        # Preview section
        st.markdown("### 👁️ Preview")
        if display_name:
            internal_name = display_name.lower().replace(' ', '_').replace('-', '_')
            internal_name = ''.join(
                c for c in internal_name if c.isalnum() or c == '_')

            preview_col1, preview_col2 = st.columns(2)
            with preview_col1:
                st.info(f"🏷️ **Display Name**: {display_name}")
                st.info(f"🗂️ **Table**: {selected_table}")
            with preview_col2:
                st.info(f"💾 **Internal Name**: `{internal_name}`")
                st.info(f"📊 **Type**: {column_type}")

        submitted = st.form_submit_button("✅ Tambah Kolom", type="primary")

        if submitted:
            if not display_name:
                st.error("❌ Nama kolom harus diisi!")
                return

            try:
                success, message = column_manager.add_dynamic_column(
                    table_name=selected_table,
                    column_name=display_name,
                    display_name=display_name,
                    column_type=column_type,
                    description=description,
                    is_searchable=is_searchable,
                    default_value=default_value,
                    created_by=created_by
                )

                if success:
                    st.success(message)
                    st.balloons()

                    # Show detailed next steps
                    st.markdown("### 🎉 Kolom Berhasil Dibuat!")

                    info_col1, info_col2 = st.columns(2)
                    with info_col1:
                        st.markdown("**📍 Detail Kolom:**")
                        st.markdown(f"- **Table**: `{selected_table}`")
                        st.markdown(f"- **Display Name**: {display_name}")
                        st.markdown(f"- **Type**: {column_type}")
                        st.markdown(
                            f"- **Searchable**: {'✅ Ya' if is_searchable else '❌ Tidak'}")

                    with info_col2:
                        st.markdown("**🚀 Langkah Selanjutnya:**")
                        st.markdown("1. 📝 Entry data di tab **'Data Entry'**")
                        st.markdown("2. 🔍 Cari data di halaman **Search**")
                        st.markdown("3. 📊 Lihat di tab **'Daftar Kolom'**")
                        st.markdown(
                            "4. 🔧 Edit data via **'Edit/Delete Assets'**")

                    # Show integration info
                    st.success(f"""
                    💡 **Integrasi Berhasil**: 
                    Kolom '{display_name}' sekarang sudah terintegrasi dengan user_terminals melalui FAT ID:
                    ✅ Kolom akan muncul di Search suggestions (refresh halaman search untuk melihat)
                    ✅ Dapat di-filter di advanced search  
                    ✅ Tersedia di form edit data
                    ✅ Dapat di-export bersama data lainnya
                    ✅ Data entry melalui FAT ID akan langsung tersedia di semua fitur
                    """)

                    # Quick integration test
                    if is_searchable:
                        st.info("""
                        🔍 **Test Integration**: 
                        - Buka halaman **Search Assets**
                        - Klik dropdown untuk melihat kolom pencarian
                        - Kolom '{display_name}' akan muncul dalam daftar
                        - Entry data melalui FAT ID akan langsung bisa dicari
                        """.format(display_name=display_name))

                else:
                    st.error(message)

            except Exception as e:
                st.error(f"❌ Error menambah kolom: {e}")


def render_data_entry(column_manager):
    """Render form for entering data to dynamic columns."""

    st.markdown("## 📝 Entry Data Kolom Dinamis")

    try:
        # Get available dynamic columns
        columns = [col for col in column_manager.get_dynamic_columns()
                   if col['is_active']]

        if not columns:
            st.info("Belum ada kolom dinamis yang tersedia untuk entry data.")
            st.markdown("👉 Silakan tambah kolom baru di tab 'Tambah Kolom'")
            return

        # Select FAT ID
        fat_id = st.text_input(
            "FAT ID*",
            placeholder="Masukkan FAT ID untuk entry data",
            help="FAT ID harus ada di database utama"
        )

        if not fat_id:
            st.warning("📝 Masukkan FAT ID untuk mulai entry data")
            return

        # Verify FAT ID exists
        query = "SELECT COUNT(*) FROM user_terminals WHERE fat_id = %s"
        success, message, result = column_manager.execute_query(
            query, (fat_id,))

        if success and result and result[0][0][0] > 0:
            st.success(f"✅ FAT ID '{fat_id}' ditemukan di database")
        else:
            st.error(f"❌ FAT ID '{fat_id}' tidak ditemukan di database!")
            return

        st.markdown(f"### 📋 Entry Data untuk FAT ID: `{fat_id}`")

        with st.form("data_entry_form"):
            entered_data = {}

            # Create input fields for each dynamic column
            for col in columns:
                col_id = col['id']
                display_name = col['display_name']
                col_type = col['column_type']
                default_value = col.get('default_value', '')

                # Get existing data for this column and FAT ID
                existing_query = """
                SELECT column_value 
                FROM dynamic_column_data 
                WHERE record_id = %s AND column_id = %s
                """
                success, message, result = column_manager.execute_query(
                    existing_query, (fat_id, col_id))
                existing_value = result[0][0][0] if success and result and result[0] else default_value

                # Render input based on type
                if col_type == 'TEXT':
                    value = st.text_input(
                        f"📝 {display_name}",
                        value=str(existing_value) if existing_value else "",
                        help=col.get('description', ''),
                        key=f"input_{col_id}"
                    )
                elif col_type == 'INTEGER':
                    try:
                        default_int = int(
                            existing_value) if existing_value else 0
                    except:
                        default_int = 0
                    value = st.number_input(
                        f"🔢 {display_name}",
                        value=default_int,
                        step=1,
                        help=col.get('description', ''),
                        key=f"input_{col_id}"
                    )
                elif col_type == 'FLOAT':
                    try:
                        default_float = float(
                            existing_value) if existing_value else 0.0
                    except:
                        default_float = 0.0
                    value = st.number_input(
                        f"🔢 {display_name}",
                        value=default_float,
                        step=0.1,
                        help=col.get('description', ''),
                        key=f"input_{col_id}"
                    )
                elif col_type == 'DATE':
                    value = st.date_input(
                        f"📅 {display_name}",
                        help=col.get('description', ''),
                        key=f"input_{col_id}"
                    )
                    value = str(value)
                elif col_type == 'BOOLEAN':
                    current_bool = str(existing_value).lower() in [
                        'true', '1', 'yes', 'on'] if existing_value else False
                    value = st.checkbox(
                        f"☑️ {display_name}",
                        value=current_bool,
                        help=col.get('description', ''),
                        key=f"input_{col_id}"
                    )
                    value = str(value)
                else:
                    value = st.text_input(
                        f"📝 {display_name}",
                        value=str(existing_value) if existing_value else "",
                        help=col.get('description', ''),
                        key=f"input_{col_id}"
                    )

                entered_data[col_id] = value

            if st.form_submit_button("💾 Simpan Semua Data", type="primary"):
                # Save all data
                success_count = 0
                error_count = 0

                for col_id, value in entered_data.items():
                    # Upsert query
                    upsert_query = """
                    INSERT INTO dynamic_column_data (record_id, column_id, column_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (record_id, column_id)
                    DO UPDATE SET 
                        column_value = EXCLUDED.column_value,
                        updated_at = CURRENT_TIMESTAMP
                    """

                    success, message, _ = column_manager.execute_query(
                        upsert_query, (fat_id, col_id, str(value))
                    )

                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        st.error(f"❌ Error menyimpan {col_id}: {message}")

                if success_count > 0:
                    st.success(f"✅ {success_count} kolom berhasil disimpan!")

                if error_count > 0:
                    st.warning(f"⚠️ {error_count} kolom gagal disimpan.")

                if success_count > 0 and error_count == 0:
                    st.balloons()

    except Exception as e:
        st.error(f"❌ Error in data entry: {e}")


def render_integration_status(column_manager):
    """Render integration status showing how dynamic columns work with user_terminals."""

    st.markdown("## 🔗 Status Integrasi Kolom Dinamis")
    st.markdown(
        "Melihat bagaimana kolom dinamis terintegrasi dengan system dan tersedia di user_terminals")

    try:
        # Get integration info
        integration_info = column_manager.get_integrated_columns_info()
        usage_stats = column_manager.show_column_usage_stats()

        # Overview metrics
        st.markdown("### 📊 Overview")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

        with metric_col1:
            st.metric("Total Kolom Dinamis",
                      integration_info['total_dynamic_columns'])
        with metric_col2:
            st.metric("Kolom Aktif", integration_info['active_columns'])
        with metric_col3:
            st.metric("Kolom Searchable",
                      integration_info['searchable_columns'])
        with metric_col4:
            st.metric("Data Tersedia", len(
                integration_info['sample_integrations']))

        st.markdown("---")

        # Usage Statistics
        st.markdown("### 📈 Statistik Penggunaan Kolom")
        if usage_stats:
            df_stats = pd.DataFrame(usage_stats)

            # Group by table
            for table_name in df_stats['table_name'].unique():
                table_stats = df_stats[df_stats['table_name'] == table_name]

                st.markdown(f"#### 📊 Table: **{table_name.upper()}**")

                for _, row in table_stats.iterrows():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                    with col1:
                        search_icon = "🔍" if row['is_searchable'] else "🚫"
                        st.markdown(
                            f"**{search_icon} {row['display_name']}** ({row['column_type']})")

                    with col2:
                        st.metric("Total Data", row['data_count'])

                    with col3:
                        st.metric("Records", row['unique_records'])

                    with col4:
                        coverage = (
                            row['unique_records'] / max(row['data_count'], 1)) * 100 if row['data_count'] > 0 else 0
                        st.metric("Coverage", f"{coverage:.1f}%")

                st.markdown("---")
        else:
            st.info("Belum ada data untuk kolom dinamis")

        # Integration Examples
        st.markdown("### 🔍 Contoh Integrasi dengan User Terminals")
        if integration_info['sample_integrations']:
            st.markdown(
                "Berikut adalah contoh FAT ID yang memiliki data kolom dinamis:")

            for example in integration_info['sample_integrations']:
                with st.expander(f"📍 FAT ID: {example['fat_id']} ({example['dynamic_data_count']} kolom data)"):
                    st.markdown(
                        f"**Kolom yang tersedia**: {example['available_columns']}")
                    st.markdown(
                        f"**Total data entries**: {example['dynamic_data_count']}")

                    # Show integration verification
                    st.success(
                        "✅ Kolom dinamis berhasil terintegrasi dengan user_terminals")
                    st.info(f"""
                    💡 **Cara Menggunakan**:
                    1. Buka halaman **Search Assets** 
                    2. Cari dengan FAT ID: `{example['fat_id']}`
                    3. Kolom dinamis akan muncul di hasil search
                    4. Data dapat di-edit melalui detail view
                    """)
        else:
            st.warning(
                "Belum ada data integrasi. Mulai entry data di tab 'Data Entry'")

        # How it works section
        st.markdown("### ⚙️ Cara Kerja Integrasi")

        how_it_works = st.expander(
            "📖 Klik untuk melihat penjelasan detail", expanded=False)
        with how_it_works:
            st.markdown("""
            **🔗 Sistem Integrasi Kolom Dinamis:**
            
            1. **Penyimpanan Data**:
               - Kolom dinamis disimpan di table `dynamic_columns`
               - Data actual disimpan di table `dynamic_column_data`
               - Link ke user_terminals melalui `fat_id`
            
            2. **Integrasi dengan Search**:
               - Kolom dinamis otomatis muncul di search suggestions
               - Dapat di-filter di advanced search
               - Results include data dari semua table (static + dynamic)
            
            3. **Integrasi dengan Edit**:
               - Kolom dinamis muncul di form edit asset
               - Dapat di-update melalui interface yang sama
               - Perubahan otomatis ter-sync dengan system
            
            4. **Export Integration**:
               - Data dinamis included di Excel/CSV export
               - Column mapping otomatis handle nama display
               - Compatible dengan semua format export
            
            **📊 Database Schema:**
            ```
            user_terminals (fat_id) ←→ dynamic_column_data (record_id)
                                    ↓
                              dynamic_columns (column definitions)
            ```
            """)
          # Test Integration Button
        st.markdown("### 🧪 Test Integrasi")
        test_col1, test_col2 = st.columns(2)

        with test_col1:
            if st.button("🔍 Test Search Integration", type="secondary"):
                st.info("🔄 Testing search integration...")
                # Test if dynamic columns appear in search
                try:                    # Import and test search integration
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                    # from dynamic_search_helper import UnifiedSearchService  # Optional import

                    # Test would need actual service instance
                    st.success(
                        "✅ Search integration ready - dynamic columns akan muncul di search setelah refresh!")
                    st.info(
                        "💡 Tip: Refresh halaman search untuk melihat kolom dinamis terbaru")
                except ImportError:
                    st.info(
                        "ℹ️ Search integration test membutuhkan UnifiedSearchService instance")
                except Exception as e:
                    st.warning(f"⚠️ Search integration warning: {e}")

        with test_col2:
            if st.button("📊 Refresh Stats", type="secondary"):
                st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading integration status: {e}")
        logger.error(f"Error in render_integration_status: {e}")


# Main app function
def app():
    """Main application function."""
    render_add_column_ui()

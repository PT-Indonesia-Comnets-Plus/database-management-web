# core/services/agent_graph/tool_sql_agent.py
import re
import json
import streamlit as st
import psycopg2
from typing import Optional, Tuple, List, Dict
from psycopg2 import pool, OperationalError, InterfaceError
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from ...utils.load_config import TOOLS_CFG
from ...utils.database import execute_with_retry

# =====================
# === Helper Functions ===
# =====================


def _get_db_schema(db_pool: pool.SimpleConnectionPool) -> Optional[Dict[str, List[str]]]:
    """
    Mengambil skema (nama tabel, kolom, tipe data, dan DESKRIPSI) dari database,
    diperkaya dengan pengetahuan kontekstual.
    """
    def _fetch_schema(conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name IN (
                    'user_terminals', 'clusters', 'home_connecteds',
                    'dokumentasis', 'additional_informations', 'pelanggans'
                )
                ORDER BY table_name, ordinal_position;
            """)
            rows = cur.fetchall()

        table_descriptions = {
            "pelanggans": "Menyimpan data unik untuk setiap pelanggan atau permohonan layanan. Setiap baris di tabel ini adalah SATU pelanggan.",
            "user_terminals": "Data master untuk semua perangkat keras jaringan seperti OLT, FDT, dan FAT. Primary key-nya adalah fat_id.",
            "clusters": "Informasi pengelompokan geografis (lokasi) untuk setiap FAT ID, termasuk kota, kecamatan, dll.",
            "home_connecteds": "Berisi data jumlah pelanggan yang terhubung (Home Connected/HC) yang terkait dengan FAT tertentu.",
            "dokumentasis": "Menyimpan link dan keterangan terkait dokumentasi teknis aset.",
            "additional_informations": "Berisi informasi tambahan terkait aset seperti mitra, tanggal RFS, dan kategori."
        }

        column_descriptions = {
            "pelanggans": {
                "id_permohonan": "PRIMARY KEY unik untuk setiap pelanggan. GUNAKAN `COUNT(id_permohonan)` UNTUK MENGHITUNG JUMLAH TOTAL PELANGGAN.",
                "fat_id": "FOREIGN KEY yang menghubungkan pelanggan ke perangkat FAT di tabel 'user_terminals'."
            },
            "user_terminals": {
                "fat_id": "PRIMARY KEY unik untuk setiap perangkat Fiber Access Terminal (FAT).",
                "brand_olt": "Merek atau vendor dari perangkat OLT (Optical Line Terminal).",
                "keterangan_full": "Keterangan apakah kapasitas FAT sudah penuh. Bisa berisi kata 'full'."
            },
            "clusters": {
                "kota_kab": "Nama kota atau kabupaten tempat aset berada. Gunakan untuk filter lokasi geografis.",
                "fat_id": "FOREIGN KEY yang menghubungkan cluster ke FAT di tabel 'user_terminals'."
            },
            "home_connecteds": {
                "total_hc": "Angka yang menunjukkan jumlah total Home Connected (pelanggan aktif) pada suatu FAT.",
                "fat_id": "FOREIGN KEY yang menghubungkan data HC ke FAT di tabel 'user_terminals'."
            }
        }
        # ===============================================

        schema = {}
        for table, column, dtype in rows:
            table_desc = table_descriptions.get(
                table, "Tidak ada deskripsi tabel.")
            col_desc = column_descriptions.get(table, {}).get(
                column, "Tidak ada deskripsi kolom.")

            if table not in schema:
                schema[table] = {"description": table_desc, "columns": []}

            schema[table]["columns"].append(f"{column} ({dtype}): {col_desc}")

        return schema

    try:
        # Gunakan retry logic Anda atau yang ada di atas
        return execute_with_retry(db_pool, _fetch_schema, max_retries=3)
    except (OperationalError, InterfaceError) as e:
        print(f"❌ Database connection error getting schema: {e}")
        return None
    except Exception as e:
        print(f"❌ Error getting DB schema: {e}")
        return None


def _generate_sql_query_from_question(schema: Dict[str, Dict[str, any]], user_question: str) -> Optional[str]:
    """
    Generates an SQL SELECT query from a natural language user question using Gemini model.
    """
    try:
        sql_model = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.sql_agent_llm,
            temperature=TOOLS_CFG.sql_agent_llm_temperature,
        )

        schema_details_list = []
        for table_name, table_info in schema.items():
            table_description = table_info.get(
                "description", f"Tabel {table_name}")
            columns_details = "\n".join(
                [f"  - {c}" for c in table_info.get("columns", [])])
            schema_details_list.append(
                f"Tabel '{table_name}': {table_description}\n  Kolom:\n{columns_details}")
        schema_str = "\n\n".join(schema_details_list)

        if len(schema_str) > 7000:
            schema_str = schema_str[:7000] + \
                "...\n(dipangkas karena terlalu panjang)"

        few_shot_examples = """
        Contoh-contoh Pertanyaan dan Query SQL yang Benar:

        Pertanyaan: "berapa total pelanggan di jember"
        Query SQL: SELECT COUNT(T1.id_permohonan) FROM pelanggans AS T1 JOIN clusters AS T2 ON T1.fat_id = T2.fat_id WHERE LOWER(T2.kota_kab) = 'jember';

        Pertanyaan: "Sebutkan semua brand OLT yang ada."
        Query SQL: SELECT DISTINCT brand_olt FROM user_terminals WHERE brand_olt IS NOT NULL AND brand_olt != '';

        Pertanyaan: "Berapa jumlah FAT yang keterangannya full di kota Surabaya?"
        Query SQL: SELECT COUNT(ut.fat_id) FROM user_terminals ut JOIN clusters cl ON ut.fat_id = cl.fat_id WHERE LOWER(ut.keterangan_full) LIKE '%full%' AND LOWER(cl.kota_kab) = 'surabaya';
        """

        prompt = f"""
        Anda adalah ahli SQL PostgreSQL yang sangat teliti. Tugas Anda adalah membuat SATU query SQL SELECT yang paling sesuai berdasarkan skema database yang detail dan pertanyaan pengguna.

        Pedoman Penting:
        1. **Pahami Skema**: Gunakan deskripsi pada skema untuk memahami makna setiap tabel dan kolom. Ini adalah kunci untuk membuat query yang relevan.
        3. **Hanya SELECT**: Hanya buat query SELECT. Jangan pernah membuat query INSERT, UPDATE, atau DELETE.
        4. **Case-Insensitive**: Selalu gunakan `LOWER()` pada kolom teks dan nilai string di klausa `WHERE` (contoh: `LOWER(T2.kota_kab) = 'jember'`).
        5. **Gunakan JOIN**: Gunakan `JOIN` antar tabel jika informasi yang diminta ada di beberapa tabel. Kunci utama untuk join adalah `fat_id`.
        6. **Output Bersih**: Output HANYA berupa query SQL mentah tanpa penjelasan, tanpa ```sql, dan tanpa ```.
        7. **GROUP BY**: Jika pertanyaan meminta data per-kategori (misal "total pelanggan di setiap kota"), gunakan `GROUP BY` untuk memisahkan hasilnya.

        Berikut adalah Skema Database Detail (termasuk deskripsi fungsional):
        {schema_str}

        Berikut adalah contoh kasus untuk membantu Anda:
        {few_shot_examples}

        Pertanyaan Pengguna:
        {user_question}

        Query SQL:
        """

        response = sql_model.invoke(prompt)
        query = re.sub(r"```sql\s*|\s*```", "",
                       response.content.strip(), flags=re.IGNORECASE)

        print(f"[DEBUG] Generated SQL Query: {query}")
        st.session_state['last_sql_query'] = query

        if not query.lower().startswith("select"):
            print(f"⚠️ Peringatan: Query bukan SELECT: {query}")
            return "Error: Gagal menghasilkan query SELECT yang valid."

        return query

    except Exception as e:
        print(f"❌ Error Gemini saat generate SQL: {e}")
        return None


def _execute_sql_query(query: str, db_pool: pool.SimpleConnectionPool) -> Tuple[Optional[List[Tuple]], Optional[List[str]], Optional[str]]:
    """
    Executes an SQL query and returns results and column names.
    """
    def _execute_operation(conn):
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description:
                return cur.fetchall(), [desc[0] for desc in cur.description], None
            else:
                conn.commit()
                return [], [], f"Non-SELECT query executed (affected rows: {cur.rowcount})"

    try:
        return execute_with_retry(db_pool, _execute_operation, max_retries=3)
    except psycopg2.Error as db_err:
        print(f"❌ Database error: {db_err}")
        # Mengembalikan pesan error yang lebih spesifik ke LLM
        return None, None, f"Query Gagal: {db_err}"
    except Exception as e:
        print(f"❌ General SQL execution error: {e}")
        return None, None, str(e)


def _generate_natural_answer_from_results(question: str, results: List[Tuple], colnames: List[str]) -> str:
    """
    Converts SQL results into a natural language response using Gemini.
    """
    try:
        model = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=TOOLS_CFG.primary_agent_llm_temperature,
        )

        if not results:
            table_str = "Tidak ada data yang ditemukan."
        else:
            table_str = f"Kolom: {' | '.join(colnames)}\nData:\n" + "\n".join(
                [" | ".join(map(str, row)) for row in results]
            )
            if len(table_str) > 5000:
                table_str = table_str[:5000] + "\n...(dipotong)"

        prompt = f"""
        Anda adalah asisten AI yang menjelaskan hasil query data ICONNET dalam bahasa Indonesia yang jelas dan ringkas.

        Pertanyaan Awal Pengguna:
        {question}

        Data Hasil Query:
        {table_str}

        Tugas Anda adalah merangkum data di atas menjadi jawaban yang langsung dan mudah dimengerti untuk menjawab pertanyaan awal pengguna.
        Jika data kosong, sampaikan bahwa tidak ada data yang ditemukan untuk permintaan tersebut.
        Jika ada data, sebutkan hasilnya secara langsung. Contoh: 'Jumlah total pelanggan di Jember adalah 5.432 orang.'

        Jawaban Anda:
        """

        return model.invoke(prompt).content.strip()

    except Exception as e:
        print(f"❌ Error merangkum hasil: {e}")
        fallback = f"Kolom: {' | '.join(colnames)}\nData:\n" + "\n".join(
            [" | ".join(map(str, row)) for row in results[:5]])
        return f"Gagal merangkum. Berikut adalah data mentahnya:\n{fallback[:1000]}..."

# =====================
# === Tool Definition ===
# =====================


@tool
def query_asset_database(user_question: str) -> str:
    """
    Menghasilkan jawaban alami berdasarkan data aset ICONNET dari database.

    Args:
        user_question (str): Pertanyaan terkait data aset ICONNET.    Returns:
        str: Ringkasan hasil atau pesan error.
    """
    print(
        f"\n🛠️ Running tool: query_asset_database\nQuestion: {user_question}")

    # Try to get database pool from session state first
    db_pool = None
    if hasattr(st, 'session_state') and st.session_state.get("db"):
        db_pool = st.session_state.get("db")
    else:
        # Fallback: Create connection pool directly
        try:
            from ...utils.database import connect_db
            db_pool, _ = connect_db()
        except Exception as e:
            print(f"Failed to create database connection: {e}")

    if not db_pool:
        return "Error: Tidak ada koneksi ke database."

    try:
        schema = _get_db_schema(db_pool)
        if schema is None:
            return "Gagal mendapatkan skema database."

        sql_query = _generate_sql_query_from_question(schema, user_question)
        if not sql_query:
            return "Tidak dapat membuat query SQL dari pertanyaan."

        results, columns, error = _execute_sql_query(sql_query, db_pool)
        if error:
            return f"Kesalahan saat menjalankan query: {error}"

        return _generate_natural_answer_from_results(user_question, results, columns)

    except Exception as e:
        print(f"❌ Error: {e}")
        return "Kesalahan tidak terduga saat menjalankan query aset."

# =====================
# === Tool Definition for Structured Data ===
# =====================


@tool
def sql_agent(user_question: str) -> str:
    """
    SQL Agent yang menghasilkan data terstruktur dalam format JSON dari database aset ICONNET.
    Tool ini dapat digunakan untuk query data biasa maupun untuk keperluan visualisasi.    Args:
        user_question (str): Pertanyaan terkait data aset ICONNET.

    Returns:
        str: Data dalam format JSON yang terstruktur, atau pesan error.
    """
    print(
        f"\n🛠️ Running tool: sql_agent\nQuestion: {user_question}")

    # Try to get database pool from session state first
    db_pool = None
    if hasattr(st, 'session_state') and st.session_state.get("db"):
        db_pool = st.session_state.get("db")
    else:
        # Fallback: Create connection pool directly
        try:
            from ...utils.database import connect_db
            db_pool, _ = connect_db()
        except Exception as e:
            print(f"Failed to create database connection: {e}")

    if not db_pool:
        return "Error: Tidak ada koneksi ke database."

    try:
        schema = _get_db_schema(db_pool)
        if schema is None:
            return "Gagal mendapatkan skema database."

        sql_query = _generate_sql_query_from_question(schema, user_question)
        if not sql_query:
            return "Tidak dapat membuat query SQL dari pertanyaan."

        results, columns, error = _execute_sql_query(sql_query, db_pool)
        if error:
            return f"Kesalahan saat menjalankan query: {error}"

        if not results:
            return "Tidak ada data yang ditemukan untuk divisualisasikan."

        # Convert results to JSON format for visualization
        structured_data = []
        for row in results:
            row_dict = {}
            for i, col_name in enumerate(columns):
                row_dict[col_name] = row[i]
            structured_data.append(row_dict)

        # Return as JSON string
        return json.dumps(structured_data, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error: {e}")
        return "Kesalahan tidak terduga saat menjalankan SQL agent."

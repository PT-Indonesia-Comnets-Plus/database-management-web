# core/services/agent_graph/tool_sql_agent.py

import os
import re
import streamlit as st
import psycopg2
import google.generativeai as genai

from typing import Optional, Tuple, List, Dict
from psycopg2 import pool
from langchain_core.tools import tool
from .load_config import TOOLS_CFG


# --- Helper Functions ---

def _get_db_schema(db_pool: pool.SimpleConnectionPool) -> Optional[Dict[str, List[str]]]:
    """Mengambil skema tabel relevan dari database."""
    conn = None
    try:
        conn = db_pool.getconn()
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

        if not rows:
            return {}

        schema = {}
        for table, column, dtype in rows:
            schema.setdefault(table, []).append(f"{column} ({dtype})")
        return schema

    except Exception as e:
        print(f"❌ Error getting DB schema: {e}")
        return None

    finally:
        if conn:
            db_pool.putconn(conn)


def _generate_sql_query_from_question(schema: Dict[str, List[str]], user_question: str) -> Optional[str]:
    """Membuat query SQL dari pertanyaan pengguna menggunakan Gemini."""
    try:
        model = genai.GenerativeModel(TOOLS_CFG.sql_agent_llm)

        schema_str = "\n".join(
            f"Tabel {t}:\n" + "\n".join([f" - {c}" for c in cs])
            for t, cs in schema.items()
        )
        max_schema_length = 5000
        if len(schema_str) > max_schema_length:
            schema_str = schema_str[:max_schema_length] + "...\n(dipangkas)"

        prompt = f"""
        Anda adalah ahli SQL PostgreSQL. Tugas Anda adalah membuat SATU query SQL SELECT berdasarkan skema database dan pertanyaan pengguna.
        Pedoman:
        1. Hanya buat query SELECT. JANGAN buat query INSERT, UPDATE, DELETE, atau DDL lainnya.
        2. Gunakan LOWER() pada kolom dan nilai untuk perbandingan string agar tidak case-sensitive.
        3. Jika pertanyaan ambigu, buat query yang paling mungkin.
        4. Pastikan nama tabel dan kolom sesuai skema. Gunakan JOIN jika perlu. Kunci utama umum adalah 'fat_id'.
        5. Hanya tampilkan query SQL mentah tanpa ```.

        Skema Database:
        {schema_str}

        Pertanyaan Pengguna:
        {user_question}

        Query SQL:
        """

        response = model.generate_content(prompt)
        sql_query = re.sub(r"```sql\s*|\s*```", "",
                           response.text.strip(), flags=re.IGNORECASE)

        if not sql_query.lower().startswith("select"):
            print(
                f"⚠️ Peringatan: Query yang dihasilkan bukan SELECT: {sql_query}")
            return None

        return sql_query

    except Exception as e:
        print(f"❌ Error Gemini saat generate SQL: {e}")
        return None


def _execute_sql_query(query: str, db_pool: pool.SimpleConnectionPool) -> Tuple[Optional[List[Tuple]], Optional[List[str]], Optional[str]]:
    """Mengeksekusi query SQL dan mengembalikan hasil, nama kolom, atau pesan error."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description:
                data = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return data, columns, None
            else:
                conn.commit()
                return [], [], f"Query non-SELECT dieksekusi (baris terpengaruh: {cur.rowcount})"

    except psycopg2.Error as db_err:
        print(f"❌ Error database saat eksekusi SQL: {db_err}")
        if conn:
            conn.rollback()
        return None, None, f"Database Error: {db_err}"

    except Exception as e:
        print(f"❌ Error umum saat eksekusi SQL: {e}")
        if conn:
            conn.rollback()
        return None, None, f"Execution Error: {e}"

    finally:
        if conn:
            db_pool.putconn(conn)


def _generate_natural_answer_from_results(question: str, results: List[Tuple], colnames: List[str]) -> str:
    """Membuat jawaban bahasa alami dari hasil query SQL."""
    try:
        model = genai.GenerativeModel(TOOLS_CFG.sqlagent_llm)

        table_str = f"Kolom: {' | '.join(colnames)}\nData:\n" + "\n".join(
            [" | ".join(map(str, row)) for row in results]
        )

        if len(table_str) > 5000:
            table_str = table_str[:5000] + "\n...(dipotong)"

        prompt = f"""
        Anda adalah asisten AI yang membantu menjelaskan hasil dari database dalam bahasa Indonesia yang alami dan mudah dimengerti.

        Pertanyaan Pengguna:
        {question}

        Data Hasil Query:
        {table_str}

        Tugas Anda:
        - Berikan ringkasan atau penjelasan singkat mengenai data di atas.
        - Jika data kosong, katakan tidak ada data.
        - Hindari menyebut 'query' atau 'SQL'. Fokus pada isi informasi.

        Jawaban Anda:
        """

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"❌ Error Gemini saat merangkum hasil SQL: {e}")
        return f"Gagal merangkum hasil. Data mentah:\n{table_str}"


# --- Tool Definition ---

@tool
def query_asset_database(user_question: str) -> str:
    """
    **[PENTING UNTUK LLM]** Gunakan tool ini HANYA untuk menjawab pertanyaan tentang **data terstruktur spesifik yang ada di database aset perusahaan ICONNET**. Tool ini akan menjalankan query SQL dan mengembalikan hasilnya.

    **Contoh Kasus Penggunaan:**
    - Jumlah/Daftar Aset: 'berapa total OLT aktif?', 'daftar FAT di cluster Surabaya Barat', 'list pelanggan di FAT X'
    - Detail Aset Spesifik: 'tampilkan detail OLT hostname XYZ', 'apa status FAT-ABC-001?', 'kapan tanggal RFS untuk PA-123?'
    - Lokasi Aset: 'di mana lokasi FDT-DEF-002?'
    - Informasi Numerik/Statistik dari Database: 'hitung rata-rata kapasitas splitter FAT per kota', 'total HC per area KP'

    **JANGAN gunakan tool ini untuk:**
    - Mencari penjelasan prosedur, kebijakan, atau definisi umum -> Gunakan 'search_internal_documents'.
    - Mencari berita terbaru, informasi umum di luar data aset ICONNET, atau cuaca -> Gunakan tool pencarian internet ('TavilySearchResults').
    - Pertanyaan yang jawabannya kemungkinan ada di dokumen PDF internal.

    Input:
        user_question (str): Pertanyaan spesifik pengguna tentang data aset ICONNET.

    Output:
        str: JSON string yang berisi:
             - 'summary' (str): Ringkasan jawaban dalam bahasa alami (dibuat dari data).
             - 'data' (Optional[List[List[Any]]]): Data mentah hasil query (list of lists), atau null.
             - 'columns' (Optional[List[str]]): Nama kolom hasil query, atau null.
             Jika terjadi error, 'summary' akan berisi pesan error.
    """

    print(
        f"🛠️ Executing SQL Tool: query_asset_database with question: '{user_question}'")

    db_pool = st.session_state.get("db")
    if not db_pool:
        print("❌ Error SQL Tool: Database connection pool not found.")
        return "Error: Database connection not available for querying assets."

    try:
        # Step 1: Get Schema
        schema = _get_db_schema(db_pool)
        if schema is None:
            return "Gagal mendapatkan skema database aset."

        # Step 2: Generate SQL Query
        sql_query = _generate_sql_query_from_question(schema, user_question)
        if sql_query is None:
            return "Maaf, saya tidak dapat membuat query SQL yang valid untuk pertanyaan tersebut."
        print(f"📝 Generated SQL Query:\n{sql_query}")

        # Step 3: Execute Query
        results, columns, error_msg = _execute_sql_query(sql_query, db_pool)
        if error_msg:
            return f"Terjadi kesalahan saat mengakses database: {error_msg}"
        if results is None:
            return "Terjadi kesalahan tidak terduga saat menjalankan query database."

        # Step 4: Generate Natural Answer
        answer = _generate_natural_answer_from_results(
            user_question, results, columns)
        return answer

    except Exception as e:
        print(f"❌ Unexpected error in SQL tool function: {e}")
        return f"Error processing database query: {e}"

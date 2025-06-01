# core/services/agent_graph/tool_sql_agent.py
import re
import json
import streamlit as st
import psycopg2
from typing import Optional, Tuple, List, Dict
from psycopg2 import pool
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.chat_models import ChatOllama
from ...utils.load_config import TOOLS_CFG

# =====================
# === Helper Functions ===
# =====================


def _get_db_schema(db_pool: pool.SimpleConnectionPool) -> Optional[Dict[str, List[str]]]:
    """
    Retrieves the relevant schema (table names and columns) from the database.

    Args:
        db_pool (SimpleConnectionPool): Database connection pool.

    Returns:
        dict: Dictionary with table names as keys and list of column info as values.
        None: If an error occurs.
    """
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
    """
    Generates an SQL SELECT query from a natural language user question using Gemini model.
    Returns the query string (and logs it).
    """
    try:
        sql_model = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.sql_agent_llm,
            temperature=TOOLS_CFG.sql_agent_llm_temperature,
        )

        schema_str = "\n".join(
            f"Tabel {t}:\n" + "\n".join([f" - {c}" for c in cs])
            for t, cs in schema.items()
        )

        if len(schema_str) > 5000:
            schema_str = schema_str[:5000] + "...\n(dipangkas)"

        mapping_hint = """
        Catatan penting:
        - Istilah 'HC' pada pertanyaan berarti 'home connected' dan data terkait terdapat pada tabel/kolom 'home_connecteds'.
        - Abaikan makna lain seperti 'human capital'.
        """

        prompt = f"""
        Anda adalah ahli SQL PostgreSQL. Tugas Anda adalah membuat SATU query SQL SELECT berdasarkan skema database dan pertanyaan pengguna.
        Pedoman:
        1. Hanya buat query SELECT. JANGAN buat query INSERT, UPDATE, DELETE, atau DDL lainnya.
        2. Gunakan LOWER() pada kolom dan nilai untuk perbandingan string agar tidak case-sensitive.
        3. Jika pertanyaan ambigu, buat query yang paling mungkin.
        4. Pastikan nama tabel dan kolom sesuai skema. Gunakan JOIN jika perlu. Kunci utama umum adalah 'fat_id'.
        5. Hanya tampilkan query SQL mentah tanpa ```.
        6. PENTING: Jika pertanyaan meminta data dari multiple lokasi/kota (misal "Surabaya dan Gresik"), 
           SELALU gunakan GROUP BY untuk memisahkan data per lokasi. JANGAN menjumlahkan semuanya jadi satu angka.
           Contoh: SELECT city, SUM(home_connecteds) FROM table WHERE city IN ('surabaya', 'gresik') GROUP BY city

        Skema:
        {schema_str}

        {mapping_hint}

        Pertanyaan:
        {user_question}

        Query SQL:
        """

        response = sql_model.invoke(prompt)
        query = re.sub(r"```sql\s*|\s*```", "",
                       response.content.strip(), flags=re.IGNORECASE)

        print(f"[DEBUG] Generated SQL Query: {query}")
        # Save to session for UI access
        st.session_state['last_sql_query'] = query

        if not query.lower().startswith("select"):
            print(f"⚠️ Peringatan: Query bukan SELECT: {query}")
            return None

        return query

    except Exception as e:
        print(f"❌ Error Gemini saat generate SQL: {e}")
        return None


def _execute_sql_query(query: str, db_pool: pool.SimpleConnectionPool) -> Tuple[Optional[List[Tuple]], Optional[List[str]], Optional[str]]:
    """
    Executes an SQL query and returns results and column names.

    Args:
        query (str): SQL query string to be executed.
        db_pool (SimpleConnectionPool): Database connection pool.

    Returns:
        Tuple of:
            - results (list of tuples): Fetched data rows.
            - columns (list of str): Column names.
            - error_msg (str): Error message, if any.
    """
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description:
                return cur.fetchall(), [desc[0] for desc in cur.description], None
            else:
                conn.commit()
                return [], [], f"Non-SELECT query executed (affected rows: {cur.rowcount})"

    except psycopg2.Error as db_err:
        print(f"❌ Database error: {db_err}")
        if conn:
            conn.rollback()
        return None, None, str(db_err)

    except Exception as e:
        print(f"❌ General SQL execution error: {e}")
        if conn:
            conn.rollback()
        return None, None, str(e)

    finally:
        if conn:
            db_pool.putconn(conn)


def _generate_natural_answer_from_results(question: str, results: List[Tuple], colnames: List[str]) -> str:
    """
    Converts SQL results into a natural language response using Gemini.

    Args:
        question (str): Original user question.
        results (list): Result set from the SQL query.
        colnames (list): List of column names.

    Returns:
        str: Natural language summary or fallback.
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

        # Deteksi apakah pertanyaan meminta visualisasi
        visualization_keywords = ['grafik', 'chart', 'plot',
                                  'visualisasi', 'buat', 'tampilkan dalam grafik', 'gambarkan']
        needs_visualization = any(keyword in question.lower()
                                  for keyword in visualization_keywords)

        if needs_visualization and results:
            # Tambahkan petunjuk untuk visualisasi dalam prompt
            prompt = f"""
            Anda adalah asisten AI yang menjelaskan hasil query data ICONNET. 
            PENTING: Pertanyaan ini mengandung permintaan visualisasi, jadi berikan jawaban yang memuat data numerik yang jelas dan terstruktur.

            Pertanyaan:
            {question}

            Data:
            {table_str}

            Berikan jawaban yang:
            1. Menjelaskan data dengan jelas
            2. Menyebutkan angka-angka spesifik dalam format yang mudah dipahami
            3. Menyiapkan data untuk visualisasi
            
            Format jawaban contoh: "Berdasarkan data yang ditemukan: Malang memiliki total 150 HC, dan Gresik memiliki total 200 HC. Data ini siap untuk divisualisasikan."

            Jawaban:
            """
        else:
            prompt = f"""
            Anda adalah asisten AI yang menjelaskan hasil query data ICONNET.

            Pertanyaan:
            {question}

            Data:
            {table_str}

            Jawaban:
            """

        return model.invoke(prompt).content.strip()

    except Exception as e:
        print(f"❌ Error merangkum hasil: {e}")
        fallback = f"Kolom: {' | '.join(colnames)}\nData:\n" + "\n".join(
            [" | ".join(map(str, row)) for row in results[:5]])
        return f"Gagal merangkum. Contoh data:\n{fallback[:1000]}..."

# =====================
# === Tool Definition ===
# =====================


@tool
def query_asset_database(user_question: str) -> str:
    """
    Menghasilkan jawaban alami berdasarkan data aset ICONNET dari database.

    Args:
        user_question (str): Pertanyaan terkait data aset ICONNET.

    Returns:
        str: Ringkasan hasil atau pesan error.
    """
    print(
        f"\n🛠️ Running tool: query_asset_database\nQuestion: {user_question}")

    db_pool = st.session_state.get("db")
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
    Tool ini dapat digunakan untuk query data biasa maupun untuk keperluan visualisasi.

    Args:
        user_question (str): Pertanyaan terkait data aset ICONNET.

    Returns:
        str: Data dalam format JSON yang terstruktur, atau pesan error.
    """
    print(
        f"\n🛠️ Running tool: sql_agent\nQuestion: {user_question}")

    db_pool = st.session_state.get("db")
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

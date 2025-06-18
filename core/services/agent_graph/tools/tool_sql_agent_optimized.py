# core/services/agent_graph/tool_sql_agent.py
import re
import json
import streamlit as st
import psycopg2
from typing import Optional, Tuple, List, Dict
from psycopg2 import pool, OperationalError, InterfaceError
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from ....utils.load_config import TOOLS_CFG
from ....utils.database import execute_with_retry

# =====================
# === Cache Variables ===
# =====================

# Cache untuk schema database - hindari fetching ulang setiap kali
_schema_cache = None

# =====================
# === Helper Functions ===
# =====================


def _get_db_schema_cached(db_pool: pool.SimpleConnectionPool) -> Optional[Dict[str, List[str]]]:
    """
    Mengambil skema database dengan caching untuk optimasi token.
    Hanya mengambil kolom yang essential dan menggunakan cache.
    """
    global _schema_cache

    # Return cached schema if available
    if _schema_cache is not None:
        return _schema_cache

    def _fetch_schema(conn):
        with conn.cursor() as cur:
            # Query yang lebih ringkas - hanya kolom essential
            cur.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name IN ('user_terminals', 'clusters', 'home_connecteds', 'pelanggans')
                AND column_name IN ('id_permohonan', 'fat_id', 'brand_olt', 'keterangan_full', 
                                    'kota_kab', 'total_hc')
                ORDER BY table_name, ordinal_position;
            """)
            rows = cur.fetchall()

        # Schema ringkas dengan deskripsi minimal namun essential
        essential_schema = {
            "pelanggans": {
                "description": "Data pelanggan. id_permohonan=PK, fat_id=FK",
                "columns": ["id_permohonan (text): PK pelanggan", "fat_id (text): FK ke user_terminals"]
            },
            "user_terminals": {
                "description": "Perangkat FAT/OLT. fat_id=PK",
                "columns": ["fat_id (text): PK perangkat", "brand_olt (text): merek OLT",
                            "keterangan_full (text): status kapasitas"]
            },
            "clusters": {
                "description": "Lokasi geografis per FAT",
                "columns": ["fat_id (text): FK ke user_terminals", "kota_kab (text): nama kota/kabupaten"]
            },
            "home_connecteds": {
                "description": "Jumlah pelanggan aktif per FAT",
                "columns": ["fat_id (text): FK ke user_terminals", "total_hc (integer): jumlah HC"]
            }
        }

        return essential_schema

    try:
        _schema_cache = execute_with_retry(
            db_pool, _fetch_schema, max_retries=2)
        return _schema_cache
    except Exception as e:
        print(f"❌ Error getting DB schema: {e}")
        return None


def _generate_sql_query_optimized(schema: Dict[str, Dict[str, any]], user_question: str) -> Optional[str]:
    """
    Generates SQL query dengan prompt yang dioptimalkan untuk mengurangi token usage.
    """
    try:
        sql_model = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.sql_agent_llm,
            temperature=TOOLS_CFG.sql_agent_llm_temperature,
        )

        # Schema ringkas
        schema_compact = []
        for table_name, table_info in schema.items():
            cols = ", ".join([col.split(" (")[0]
                             for col in table_info.get("columns", [])])
            schema_compact.append(f"{table_name}({cols})")
        schema_str = "; ".join(schema_compact)

        # Prompt yang diringkas namun tetap efektif
        prompt = f"""SQL Expert untuk PostgreSQL. Buat SELECT query untuk: "{user_question}"

Skema: {schema_str}

Aturan:
- Hanya SELECT
- Gunakan LOWER() untuk text comparison
- JOIN via fat_id
- COUNT(id_permohonan) untuk hitung pelanggan
- Output hanya SQL mentah

Contoh:
Q: "berapa pelanggan di jember"
A: SELECT COUNT(p.id_permohonan) FROM pelanggans p JOIN clusters c ON p.fat_id = c.fat_id WHERE LOWER(c.kota_kab) = 'jember';

Query:"""

        response = sql_model.invoke(prompt)
        query = re.sub(r"```sql\s*|\s*```", "",
                       response.content.strip(), flags=re.IGNORECASE)

        print(f"[DEBUG] Generated SQL: {query}")
        st.session_state['last_sql_query'] = query

        if not query.lower().startswith("select"):
            return "Error: Query bukan SELECT yang valid."

        return query

    except Exception as e:
        print(f"❌ Error generate SQL: {e}")
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
        return execute_with_retry(db_pool, _execute_operation, max_retries=2)
    except psycopg2.Error as db_err:
        print(f"❌ Database error: {db_err}")
        return None, None, f"Query Gagal: {db_err}"
    except Exception as e:
        print(f"❌ General SQL execution error: {e}")
        return None, None, str(e)


def _generate_natural_answer_optimized(question: str, results: List[Tuple], colnames: List[str]) -> str:
    """
    Converts SQL results into natural language response dengan prompt yang dioptimalkan.
    """
    try:
        model = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=TOOLS_CFG.primary_agent_llm_temperature,
        )

        if not results:
            return "Tidak ada data yang ditemukan untuk pertanyaan tersebut."

        # Batasi hasil untuk menghemat token
        limited_results = results[:10] if len(results) > 10 else results

        # Format data ringkas
        if len(limited_results) == 1 and len(limited_results[0]) == 1:
            # Single value result - langsung return
            value = limited_results[0][0]
            return f"Hasil: {value}"

        data_preview = []
        for row in limited_results[:3]:  # Hanya 3 row pertama untuk context
            data_preview.append(" | ".join(map(str, row)))

        data_str = f"Kolom: {' | '.join(colnames)}\n" + "\n".join(data_preview)
        if len(results) > 3:
            data_str += f"\n... dan {len(results)-3} baris lainnya"

        # Prompt yang diringkas
        prompt = f"""Jawab singkat dalam bahasa Indonesia untuk: "{question}"

Data:
{data_str}

Berikan jawaban langsung dan ringkas tanpa penjelasan tambahan."""

        return model.invoke(prompt).content.strip()

    except Exception as e:
        print(f"❌ Error merangkum hasil: {e}")
        # Fallback sederhana
        if len(results) == 1 and len(results[0]) == 1:
            return f"Hasil: {results[0][0]}"
        return f"Ditemukan {len(results)} baris data."

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

    # Try to get database pool from session state first
    db_pool = None
    if hasattr(st, 'session_state') and st.session_state.get("db"):
        db_pool = st.session_state.get("db")
    else:
        # Fallback: Create connection pool directly
        try:
            from ....utils.database import connect_db
            db_pool, _ = connect_db()
        except Exception as e:
            print(f"Failed to create database connection: {e}")

    if not db_pool:
        return "Error: Tidak ada koneksi ke database."

    try:
        schema = _get_db_schema_cached(db_pool)
        if schema is None:
            return "Gagal mendapatkan skema database."

        sql_query = _generate_sql_query_optimized(schema, user_question)
        if not sql_query:
            return "Tidak dapat membuat query SQL dari pertanyaan."

        results, columns, error = _execute_sql_query(sql_query, db_pool)
        if error:
            return f"Kesalahan saat menjalankan query: {error}"

        return _generate_natural_answer_optimized(user_question, results, columns)

    except Exception as e:
        print(f"❌ Error: {e}")
        return "Kesalahan tidak terduga saat menjalankan query aset."


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
    print(f"\n🛠️ Running tool: sql_agent\nQuestion: {user_question}")

    # Try to get database pool from session state first
    db_pool = None
    if hasattr(st, 'session_state') and st.session_state.get("db"):
        db_pool = st.session_state.get("db")
    else:
        # Fallback: Create connection pool directly
        try:
            from ....utils.database import connect_db
            db_pool, _ = connect_db()
        except Exception as e:
            print(f"Failed to create database connection: {e}")

    if not db_pool:
        return "Error: Tidak ada koneksi ke database."

    try:
        schema = _get_db_schema_cached(db_pool)
        if schema is None:
            return "Gagal mendapatkan skema database."

        sql_query = _generate_sql_query_optimized(schema, user_question)
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

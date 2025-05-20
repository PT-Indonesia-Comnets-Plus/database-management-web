# core/services/agent_graph/tool_sql_agent.py
import re
import streamlit as st
import psycopg2
from typing import Optional, Tuple, List, Dict
from psycopg2 import pool
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
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

    Args:
        schema (dict): Database schema containing table and column information.
        user_question (str): Question provided by the user.

    Returns:
        str: SQL SELECT query string.
        None: If an invalid query is generated.
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

        prompt = f"""
        Anda adalah ahli SQL PostgreSQL. Buat SATU query SQL SELECT berdasarkan skema dan pertanyaan berikut.

        Skema:
        {schema_str}

        Pertanyaan:
        {user_question}

        Query SQL:
        """

        response = sql_model.invoke(prompt)
        query = re.sub(r"```sql\s*|\s*```", "",
                       response.content.strip(), flags=re.IGNORECASE)

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

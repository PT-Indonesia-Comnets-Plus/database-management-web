# core/services/agent_graph/tool_rag.py

import json
from typing import List, Dict, Any

import streamlit as st
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from psycopg2 import pool

from .load_config import TOOLS_CFG


def _initialize_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Inisialisasi model embedding Google Generative AI."""
    return GoogleGenerativeAIEmbeddings(
        model=TOOLS_CFG.rag_embedding_model,
        google_api_key=TOOLS_CFG.google_api_key,
    )


def _fetch_similar_documents(
    query_embedding: List[float],
    db_conn: pool.SimpleConnectionPool,
    k: int
) -> List[tuple]:
    """Mengambil dokumen serupa dari database berdasarkan embedding query."""
    with db_conn.cursor() as cur:
        embedding_json = json.dumps(query_embedding)
        cur.execute(
            """
            SELECT content, metadata, 1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (embedding_json, embedding_json, k)
        )
        return cur.fetchall()


def _parse_metadata(metadata_raw: Any) -> Dict[str, Any]:
    """Parse metadata dokumen dari hasil database."""
    try:
        if isinstance(metadata_raw, str):
            return json.loads(metadata_raw)
        elif isinstance(metadata_raw, dict):
            return metadata_raw
        else:
            return {"raw": str(metadata_raw)}
    except Exception:
        return {"raw": str(metadata_raw)}


def _search_similar_documents_in_db(
    query: str,
    db_pool: pool.SimpleConnectionPool,
    k: int
) -> List[Dict[str, Any]]:
    """Cari dokumen internal yang relevan berdasarkan query."""
    conn = None
    try:
        conn = db_pool.getconn()
        embeddings = _initialize_embeddings()
        query_embedding = embeddings.embed_query(query)

        results = _fetch_similar_documents(query_embedding, conn, k)

        return [
            {
                "content": content,
                "metadata": _parse_metadata(metadata_raw),
                "similarity": similarity,
            }
            for content, metadata_raw, similarity in results
        ]

    except Exception as e:
        print(f"❌ Error mencari dokumen RAG: {e}")
        return [{"error": f"Error during RAG search: {e}"}]

    finally:
        if conn:
            db_pool.putconn(conn)


@tool
def search_internal_documents(query: str) -> str:
    """
    Gunakan tool ini untuk mencari informasi spesifik dalam dokumen internal perusahaan,
    seperti prosedur standar operasi (SOP), kebijakan, panduan teknis, atau laporan lama.
    Sangat berguna untuk pertanyaan tentang 'bagaimana cara', 'apa kebijakan tentang', 'jelaskan prosedur untuk'.
    Input adalah pertanyaan atau topik yang ingin dicari.
    Output adalah ringkasan atau potongan teks relevan dari dokumen internal.
    """
    db_pool = st.session_state.get("db")
    k_results = TOOLS_CFG.rag_k

    try:
        search_results = _search_similar_documents_in_db(
            query=query,
            db_pool=db_pool,
            k=k_results,
        )

        if not search_results:
            return "Tidak ada dokumen internal yang relevan ditemukan."

        if any("error" in res for res in search_results):
            first_error = next(
                (res["error"] for res in search_results if "error" in res),
                "Unknown error during search."
            )
            return f"Gagal mencari dokumen internal: {first_error}"

        context = "\n\n---\n\n".join([
            f"Source: {res['metadata'].get('file_name', 'N/A')}\nContent: {res['content']}"
            for res in search_results
        ])

        max_context_len = 4000
        if len(context) > max_context_len:
            context = context[:max_context_len] + "\n... (truncated)"

        return context

    except Exception as e:
        print(f"❌ Unexpected error in RAG tool function: {e}")
        return f"Error processing document search: {e}"

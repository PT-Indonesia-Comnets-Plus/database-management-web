# core/services/agent_graph/tool_rag.py

import json
from typing import List, Dict, Any

import streamlit as st
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from psycopg2 import pool

from ....utils.load_config import TOOLS_CFG


def _initialize_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Initialize the Google Generative AI embedding model
    using configuration from TOOLS_CFG.

    Returns:
        GoogleGenerativeAIEmbeddings: An instance of the embedding model.
    """
    return GoogleGenerativeAIEmbeddings(
        model=TOOLS_CFG.rag_embedding_model,
        gemini_api_key=TOOLS_CFG.gemini_api_key,
    )


def _fetch_similar_documents(
    query_embedding: List[float],
    db_conn: pool.SimpleConnectionPool,
    k: int
) -> List[tuple]:
    """
    Fetch similar documents from the database based on query embeddings.

    Args:
        query_embedding (List[float]): Embedding vector of the user's query.
        db_conn (SimpleConnectionPool): Database connection pool instance.
        k (int): Number of most relevant documents to retrieve.

    Returns:
        List[tuple]: List of (content, metadata, similarity score) tuples.
    """
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
    """
    Parse metadata from raw database result.

    Args:
        metadata_raw (Any): Raw metadata string or dictionary.

    Returns:
        Dict[str, Any]: Parsed metadata dictionary.
    """
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
    """
    Search for relevant internal documents using vector similarity search.

    Args:
        query (str): User's input question or topic.
        db_pool (SimpleConnectionPool): Database connection pool.
        k (int): Number of top documents to retrieve.

    Returns:
        List[Dict[str, Any]]: List of relevant documents with metadata and similarity.
    """
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
        print(f"❌ Error while searching documents with RAG: {e}")
        return [{"error": f"Error during RAG search: {e}"}]

    finally:
        if conn:
            db_pool.putconn(conn)


@tool
def search_internal_documents(query: str) -> str:
    """
    Use this tool to search for specific information inside internal company documents,
    such as SOPs, policies, technical manuals, or archived reports.

    Best suited for questions like "how to", "what is the policy on", or "explain the procedure for".

    Args:
        query (str): The user’s question or topic to search for.

    Returns:
        str: A summarized or relevant snippet from internal documents.
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
            return "No relevant internal documents were found."

        if any("error" in res for res in search_results):
            first_error = next(
                (res["error"] for res in search_results if "error" in res),
                "Unknown error during document search."
            )
            return f"Failed to search internal documents: {first_error}"

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

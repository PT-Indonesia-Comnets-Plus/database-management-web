import streamlit as st
import json
import psycopg2
from psycopg2 import pool
from typing import List
from langchain.schema import Document
from typing import List
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.services.agent_graph.load_config import TOOLS_CFG


def check_file_exists_in_bucket(bucket_name: str, file_name: str) -> bool:
    try:
        supabase = st.session_state.storage
        files_response = supabase.storage.from_(bucket_name).list()

        if isinstance(files_response, dict) and files_response.get("error"):
            st.error(f"Error listing files: {files_response['error']}")
            return False
        elif isinstance(files_response, list):
            return any(f.get('name') == file_name for f in files_response)
        else:
            st.warning(f"Format response tidak dikenal: {files_response}")
            return False

    except Exception as e:
        st.error(f"❌ Error checking file: {e}")
        return False


def upload_file_to_supabase(file_path: str, bucket_name: str, file_name: str):
    try:
        if "storage" not in st.session_state:
            st.error("Supabase Storage belum diinisialisasi.")
            return None
        supabase = st.session_state.storage
        with open(file_path, "rb") as file:
            response = supabase.storage.from_(bucket_name).upload(
                file_name, file, file_options={'upsert': 'true'}
            )
        public_url_response = supabase.storage.from_(
            bucket_name).get_public_url(file_name)

        if isinstance(public_url_response, str):
            st.success(f"✅ File diunggah: {public_url_response}")
            return public_url_response
        elif isinstance(public_url_response, dict) and public_url_response.get("error"):
            st.error(
                f"❌ Error mendapatkan URL publik: {public_url_response['error']}")
            return None
        else:
            st.warning("File diunggah tapi URL publik gagal didapat.")
            return None
    except Exception as e:
        st.error(f"❌ Error saat upload Supabase: {e}")
        return None


def check_file_exists_in_db(db_pool: pool.SimpleConnectionPool, file_name: str) -> bool:
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            search_pattern = f'%"file_name": "{file_name}"%'
            cur.execute(
                "SELECT 1 FROM documents WHERE metadata LIKE %s LIMIT 1", (search_pattern,))
            return cur.fetchone() is not None
    except Exception as e:
        st.error(f"Error checking file in DB: {e}")
        return False
    finally:
        if conn:
            db_pool.putconn(conn)


def save_embeddings_to_db(db_pool: pool.SimpleConnectionPool, documents: List[Document], embeddings: List[List[float]], file_name: str):
    if not documents or not embeddings or len(documents) != len(embeddings):
        st.error("Jumlah dokumen dan embedding tidak cocok.")
        return

    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            delete_pattern = f'%"file_name": "{file_name}"%'
            cur.execute(
                "DELETE FROM documents WHERE metadata LIKE %s", (delete_pattern,))
            st.info(f"Menghapus embedding lama: {cur.rowcount} rows.")

            for doc, embedding in zip(documents, embeddings):
                embedding_json = json.dumps(embedding)
                metadata_json = json.dumps(
                    doc.metadata if isinstance(doc.metadata, dict) else {})

                cur.execute(
                    """
                    INSERT INTO documents (content, metadata, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (doc.page_content, metadata_json, embedding_json)
                )
            conn.commit()
            st.success("✅ Embedding berhasil disimpan.")
    except Exception as e:
        st.error(f"❌ Error database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db_pool.putconn(conn)


def load_pdf(file_path: str) -> List[Document]:
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        for doc in documents:
            doc.metadata["file_name"] = os.path.basename(file_path)
        return documents
    except Exception as e:
        st.error(f"Error loading PDF: {e}")
        return []


def split_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_documents(documents)


def create_embeddings_and_save_to_db(db_pool: pool.SimpleConnectionPool, documents: List[Document], file_name: str):
    """Generate embeddings dan simpan ke database PostgreSQL."""
    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model=TOOLS_CFG.rag_embedding_model, google_api_key=TOOLS_CFG.gemini_api_key)

        st.info("Membuat embeddings untuk potongan dokumen...")
        contents = [doc.page_content for doc in documents]
        embeddings = embeddings_model.embed_documents(contents)
        st.success("✅ Embeddings berhasil dibuat.")

        # Simpan ke Database
        save_embeddings_to_db(db_pool, documents, embeddings, file_name)
        return embeddings
    except Exception as e:
        st.error(f"❌ Gagal membuat atau menyimpan embeddings: {e}")
        return None

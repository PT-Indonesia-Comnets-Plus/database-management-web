# features/admin/views/rag.py

import os
import json
import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import List
from langchain_community.document_loaders import PyPDFLoader
import base64
# Hapus import pinecone dan time jika tidak digunakan lagi
# import pinecone
# import time
import psycopg2  # <-- Tambahkan kembali import psycopg2
from psycopg2 import pool  # <-- Pastikan pool diimpor

# Ambil API Key Google (tetap diperlukan untuk embedding)
api_key = os.getenv("GEMINI_API_KEY", st.secrets.get(
    "gemini", {}).get("api_key"))
if not api_key:
    st.error("GOOGLE_API_KEY tidak ditemukan.")
    st.stop()

# Hapus Konfigurasi Pinecone
# pinecone_api_key = st.secrets.get("pinecone", {}).get("api_key")
# pinecone_environment = st.secrets.get("pinecone", {}).get("environment")
# pinecone_index_name = st.secrets.get("pinecone", {}).get("index_name")
# if not all([pinecone_api_key, pinecone_environment, pinecone_index_name]):
#     st.error("Konfigurasi Pinecone tidak lengkap.")
#     st.stop()

# Hapus Fungsi Helper Pinecone
# @st.cache_resource
# def get_pinecone_index():
#     ...

# --- Fungsi Helper Lain (Sebagian besar sama) ---


def check_file_exists_in_bucket(bucket_name: str, file_name: str) -> bool:
    # ... (fungsi ini tetap sama, memeriksa Supabase Storage) ...
    try:
        if "storage" not in st.session_state:
            st.error("Supabase Storage belum diinisialisasi.")
            return False

        supabase = st.session_state.storage
        files_response = supabase.storage.from_(bucket_name).list()

        if isinstance(files_response, dict) and files_response.get("error"):
            st.error(
                f"Error listing files in bucket: {files_response['error']}")
            return False
        elif isinstance(files_response, list):
            return any(f.get('name') == file_name for f in files_response)
        else:
            st.warning(
                f"Format response tidak dikenal dari Supabase list(): {files_response}")
            return False

    except Exception as e:
        st.error(f"❌ Error checking file existence in bucket: {e}")
        return False

# Fungsi cek file di DB (opsional, bisa diaktifkan jika perlu)


def check_file_exists_in_db(db_pool: pool.SimpleConnectionPool, file_name: str) -> bool:
    """Memeriksa apakah dokumen dengan nama file tertentu sudah ada di tabel 'documents'."""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Query metadata JSONB: metadata @> '{"file_name": "nama_file.pdf"}'
            # Query metadata TEXT: metadata LIKE '%"file_name": "{file_name}"%' (kurang efisien)
            # Asumsi metadata adalah TEXT dan berisi JSON
            # Gunakan json_extract_path_text jika PostgreSQL versi mendukung
            # Atau cara sederhana dengan LIKE (hati-hati jika nama file muncul di tempat lain)
            # Cara lebih baik: tambahkan kolom file_name terpisah di tabel documents
            # Untuk sekarang, kita pakai LIKE pada metadata
            search_pattern = f'%"file_name": "{file_name}"%'
            cur.execute(
                "SELECT 1 FROM documents WHERE metadata LIKE %s LIMIT 1", (search_pattern,))
            exists = cur.fetchone() is not None
            return exists
    except Exception as e:
        st.error(f"Error checking file existence in DB: {e}")
        return False
    finally:
        if conn:
            db_pool.putconn(conn)


def upload_file_to_supabase(file_path: str, bucket_name: str, file_name: str):
    # ... (fungsi ini tetap sama, mengunggah ke Supabase Storage) ...
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
            st.success(
                f"✅ File berhasil diunggah/diperbarui di Supabase Storage: {public_url_response}")
            return public_url_response
        elif isinstance(public_url_response, dict) and public_url_response.get("error"):
            st.error(
                f"❌ Gagal mendapatkan URL publik: {public_url_response['error']}")
            return None
        else:
            st.warning("File diunggah tapi gagal mendapatkan URL publik.")
            return None
    except Exception as e:
        st.error(f"❌ Error saat mengunggah file ke Supabase: {e}")
        if "Duplicate" in str(e) or "already exists" in str(e):
            st.warning(f"File '{file_name}' sudah ada. Melanjutkan proses...")
            try:
                public_url_response = supabase.storage.from_(
                    bucket_name).get_public_url(file_name)
                if isinstance(public_url_response, str):
                    return public_url_response
            except Exception:
                pass
        return None


def load_pdf(file_path: str) -> List[Document]:
    # ... (fungsi ini tetap sama) ...
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
    # ... (fungsi ini tetap sama) ...
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_documents(documents)


# Hapus fungsi upsert_embeddings_to_pinecone
# def upsert_embeddings_to_pinecone(...):
#     ...

# --- Fungsi Baru/Kembalikan: Simpan ke DB Postgres ---
def save_embeddings_to_db(db_pool: pool.SimpleConnectionPool, documents: List[Document], embeddings: List[List[float]], file_name: str):
    """
    Simpan document embeddings ke tabel 'documents' di PostgreSQL.

    Args:
        db_pool: Pool koneksi database psycopg2.
        documents: List dokumen hasil chunking.
        embeddings: List vektor embedding yang sesuai.
        file_name: Nama file asal (untuk menghapus data lama jika perlu).
    """
    if not documents or not embeddings or len(documents) != len(embeddings):
        st.error("Jumlah dokumen dan embedding tidak cocok atau kosong.")
        return

    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Opsional: Hapus embedding lama untuk file ini sebelum insert baru
            # Ini berguna jika Anda ingin mengganti total knowledge dari file ini
            # Perlu cara identifikasi yang andal, misal berdasarkan metadata file_name
            st.info(
                f"Menghapus embedding lama untuk file '{file_name}' (jika ada)...")
            delete_pattern = f'%"file_name": "{file_name}"%'
            cur.execute(
                "DELETE FROM documents WHERE metadata LIKE %s", (delete_pattern,))
            st.write(f"Jumlah embedding lama yang dihapus: {cur.rowcount}")

            st.info(
                f"Menyimpan {len(documents)} embedding baru ke database...")
            insert_count = 0
            for doc, embedding in zip(documents, embeddings):
                # Pastikan embedding adalah list float
                if not isinstance(embedding, list):
                    embedding_list = embedding.tolist()  # Coba konversi jika numpy array
                else:
                    embedding_list = embedding

                # Serialisasi embedding dan metadata ke JSON string
                embedding_json = json.dumps(embedding_list)
                # Pastikan metadata adalah dict sebelum di-dump
                metadata_dict = doc.metadata if isinstance(
                    doc.metadata, dict) else {}
                metadata_json = json.dumps(metadata_dict)

                # Insert ke database
                cur.execute(
                    """
                    INSERT INTO documents (content, metadata, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (doc.page_content, metadata_json, embedding_json)
                )
                insert_count += 1
            conn.commit()  # Commit setelah semua data di-insert
            st.success(
                f"✅ {insert_count} embedding berhasil disimpan ke database.")

    except psycopg2.Error as db_err:
        st.error(f"❌ Error database saat menyimpan embeddings: {db_err}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    except Exception as e:
        st.error(f"❌ Gagal menyimpan embeddings ke database: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn:
            db_pool.putconn(conn)


def create_embeddings_and_save_to_db(db_pool: pool.SimpleConnectionPool, documents: List[Document], file_name: str):
    """Generate embeddings dan simpan ke database PostgreSQL."""
    try:
        if not api_key:
            st.error("Google API Key tidak tersedia untuk membuat embeddings.")
            return None

        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=api_key)

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

# --- Aplikasi Streamlit Utama ---


def app():
    st.title("RAG Upload File (PostgreSQL/pgvector Backend)")

    # Dapatkan koneksi pool database dari session state
    db_pool = st.session_state.get("db")
    if not db_pool:
        st.error(
            "Koneksi Database Pool tidak tersedia. Harap refresh atau cek konfigurasi.")
        st.stop()

    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_file is not None:
        file_name = uploaded_file.name
        temp_file_path = os.path.join(temp_dir, file_name)

        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"📄 Preview File {file_name}")

        try:
            base64_pdf = base64.b64encode(
                uploaded_file.getvalue()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Gagal menampilkan preview PDF: {e}")

        if st.button("🚀 Proses dan Simpan ke Database"):
            bucket_name = "document.rag"  # Nama bucket Supabase Storage Anda

            # 1. Cek & Upload ke Supabase Storage (untuk menyimpan file asli)
            file_exists_in_storage = check_file_exists_in_bucket(
                bucket_name, file_name)
            if file_exists_in_storage:
                st.warning(
                    f"⚠️ File '{file_name}' sudah ada di Supabase Storage. Mengunggah ulang (upsert)...")
            else:
                st.info(f"Mengunggah '{file_name}' ke Supabase Storage...")

            public_url = upload_file_to_supabase(
                temp_file_path, bucket_name, file_name)
            if public_url:
                st.write(f"📂 File URL (Supabase Storage): {public_url}")
            else:
                st.error(
                    "Gagal mengunggah file ke Supabase Storage. Proses embedding dibatalkan.")
                return

            # 2. Proses PDF, Buat Embeddings, dan Simpan ke Database
            # Opsional: Cek apakah file sudah diproses sebelumnya di DB
            # file_processed_in_db = check_file_exists_in_db(db_pool, file_name)
            # if file_processed_in_db:
            #     st.warning(f"⚠️ File '{file_name}' sepertinya sudah diproses sebelumnya. Embedding lama akan dihapus dan diganti.")

            st.info(f"Memulai proses dokumen '{file_name}' untuk database...")
            with st.spinner("Memuat dan membagi PDF..."):
                documents = load_pdf(temp_file_path)
                if not documents:
                    st.error("Gagal memuat dokumen PDF.")
                    return
                split_docs = split_documents(documents)
                st.write(f"Dokumen dibagi menjadi {len(split_docs)} potongan.")

            if not split_docs:
                st.warning("Tidak ada potongan dokumen yang dihasilkan.")
                return

            # Buat embeddings dan simpan ke database
            create_embeddings_and_save_to_db(db_pool, split_docs, file_name)

            st.success(
                f"✅ File '{file_name}' berhasil diproses dan disimpan ke database!")

        # Hapus file sementara (opsional)
        # if os.path.exists(temp_file_path):
        #     try: os.remove(temp_file_path)
        #     except Exception as e: st.warning(f"Gagal hapus file sementara: {e}")


if __name__ == "__main__":
    if "storage" not in st.session_state:
        st.warning("Supabase storage client tidak ditemukan di session state.")
    if "db" not in st.session_state:
        st.error("Database pool 'db' tidak ditemukan di session state.")
        # Mock jika perlu untuk testing langsung
        # try:
        #     from core.database import connect_db
        #     st.session_state.db, st.session_state.storage = connect_db()
        #     if not st.session_state.db: raise Exception("Mock DB Gagal")
        # except Exception as e:
        #     st.error(f"Gagal membuat mock DB/Storage: {e}")
        #     st.stop()

    app()

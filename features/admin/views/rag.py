import os
import json
import streamlit as st
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from typing import List
from langchain_community.document_loaders import PyPDFLoader
import base64

api_key = os.getenv("GOOGLE_API_KEY", st.secrets["google"]["api_key"])


def check_file_exists_in_bucket(bucket_name: str, file_name: str) -> bool:
    """
    Periksa apakah file sudah ada di bucket Supabase.

    Args:
        bucket_name (str): Nama bucket di Supabase Storage.
        file_name (str): Nama file yang akan diperiksa.

    Returns:
        bool: True jika file sudah ada, False jika belum.
    """
    try:
        if "storage" not in st.session_state:
            st.error("Supabase Storage belum diinisialisasi.")
            return False

        supabase = st.session_state.storage
        files = supabase.storage.from_(bucket_name).list()
        return any(f['name'] == file_name for f in files)
    except Exception as e:
        st.error(f"❌ Error checking file existence in bucket: {e}")
        return False


def check_file_exists_in_db(db, file_name: str) -> bool:
    """
    Periksa apakah file sudah ada di database berdasarkan nama file.

    Args:
        db: Database connection (st.session_state.db).
        file_name (str): Nama file yang akan diperiksa.

    Returns:
        bool: True jika file sudah ada, False jika belum.
    """
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM documents WHERE metadata->>'file_name' = %s;
            """,
            (file_name,)
        )
        result = cur.fetchone()
        return result[0] > 0
    except Exception as e:
        st.error(f"❌ Error checking file existence in database: {e}")
        return False


def upload_file_to_supabase(file_path: str, bucket_name: str, file_name: str):
    """
    Mengunggah file ke Supabase Storage.

    Args:
        file_path (str): Path file lokal yang akan diunggah.
        bucket_name (str): Nama bucket di Supabase Storage.
        file_name (str): Nama file yang akan disimpan di bucket.

    Returns:
        str: URL file yang diunggah jika berhasil, None jika gagal.
    """
    try:
        if "storage" not in st.session_state:
            st.error("Supabase Storage belum diinisialisasi.")
            return None

        supabase = st.session_state.storage

        with open(file_path, "rb") as file:
            response = supabase.storage.from_(
                bucket_name).upload(file_name, file)

        if response.get("error"):
            st.error(
                f"❌ Gagal mengunggah file: {response['error']['message']}")
            return None

        public_url = supabase.storage.from_(
            bucket_name).get_public_url(file_name)
        st.success(
            f"✅ File berhasil diunggah ke Supabase Storage: {public_url}")
        return public_url
    except Exception as e:
        st.error(f"❌ Error saat mengunggah file: {e}")
        return None


def load_pdf(file_path: str) -> List[Document]:
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return documents
    except Exception as e:
        st.error(f"Error loading PDF: {e}")
        return []


def split_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_documents(documents)


def save_embeddings_to_db(db, documents, embeddings, file_name: str):
    try:
        cur = db.cursor()
        for doc, embedding in zip(documents, embeddings):
            embedding_data = embedding if isinstance(
                embedding, list) else embedding.tolist()
            cur.execute(
                """
                INSERT INTO documents (content, metadata, embedding)
                VALUES (%s, %s, %s)
                """,
                (doc.page_content, json.dumps(
                    {**doc.metadata, "file_name": file_name}), json.dumps(embedding_data))
            )
        db.commit()
        st.success("✅ Embeddings successfully saved to the database!")
    except Exception as e:
        db.rollback()
        st.error(f"❌ Failed to save embeddings to the database: {e}")


def create_vector_store_and_save_to_db(db, documents, file_name: str):
    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001")
        embeddings = embeddings_model.embed_documents(
            [doc.page_content for doc in documents])
        save_embeddings_to_db(db, documents, embeddings, file_name)
        return embeddings
    except Exception as e:
        st.error(f"❌ Failed to create vector store: {e}")
        return None


def app():
    st.title("RAG Upload File")

    db = st.session_state.db
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_file is not None:
        file_name = uploaded_file.name
        temp_file_path = os.path.join(temp_dir, file_name)

        # Simpan file ke folder sementara
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"📄Preview File {file_name}")

        # Tampilkan preview PDF
        base64_pdf = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

        # Tombol proses
        if st.button("🚀 Proses dan Simpan"):
            bucket_name = "document.rag"

            # Periksa apakah file sudah ada di bucket
            if check_file_exists_in_bucket(bucket_name, file_name):
                st.warning(
                    "📂 File sudah ada di bucket. Melewati upload dan embedding.")
                return

            # Upload ke Supabase Storage
            public_url = upload_file_to_supabase(
                temp_file_path, bucket_name, file_name)
            if public_url:
                st.write(f"📂 File URL: {public_url}")

            # Cek database dan simpan embedding
            if check_file_exists_in_db(db, file_name):
                st.info("📂 File sudah ada di database. Melewati vector embedding.")
            else:
                st.info(
                    "📂 File belum ada di database. Memulai proses vector embedding...")
                documents = load_pdf(temp_file_path)
                if not documents:
                    return
                split_docs = split_documents(documents)
                create_vector_store_and_save_to_db(db, split_docs, file_name)

            st.success("✅ File berhasil diproses!")


if __name__ == "__main__":
    app()

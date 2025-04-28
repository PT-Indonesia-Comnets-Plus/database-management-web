import streamlit as st
from handler import (
    check_file_exists_in_bucket,
    upload_file_to_supabase,
    check_file_exists_in_db,
    save_embeddings_to_db,
    load_pdf,
    split_documents
)
from psycopg2 import pool
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
import os

# Inisialisasi koneksi DB Pool (sesuaikan confignya)
db_pool = pool.SimpleConnectionPool(
    1, 10,
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
)


def main():
    st.title("Upload dan Proses PDF dengan Supabase dan DB")

    db_pool = st.session_state.get("db")

    bucket_name = "document.rag"

    uploaded_file = st.file_uploader("Upload file PDF", type=["pdf"])
    if uploaded_file is not None:
        file_name = uploaded_file.name

        # Simpan sementara file upload ke disk lokal
        with open(file_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Cek apakah file sudah ada di bucket
        if check_file_exists_in_bucket(bucket_name, file_name):
            st.warning(f"File {file_name} sudah ada di bucket.")

        else:
            # Upload file ke Supabase Storage
            url = upload_file_to_supabase(file_name, bucket_name, file_name)
            if url:
                st.write(f"File berhasil diupload ke: {url}")

                # Load dan split dokumen PDF
                documents = load_pdf(file_name)
                if documents:
                    chunks = split_documents(documents)

                    # Buat embeddings
                    # Atur sesuai API key dan konfigurasi kamu
                    embeddings_model = OpenAIEmbeddings()
                    embeddings = [embeddings_model.embed(
                        doc.page_content) for doc in chunks]

                    # Cek dan simpan embedding ke DB
                    if check_file_exists_in_db(db_pool, file_name):
                        st.info(
                            "Embedding untuk file ini sudah ada, akan dihapus dan diganti.")

                    save_embeddings_to_db(
                        db_pool, chunks, embeddings, file_name)

        # Hapus file lokal setelah selesai
        try:
            os.remove(file_name)
        except Exception as e:
            st.warning(f"Gagal menghapus file lokal: {e}")


if __name__ == "__main__":
    main()

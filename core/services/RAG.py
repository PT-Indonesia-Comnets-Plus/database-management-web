# core/services/RAGService.py

import streamlit as st
import os
import json
import base64
from typing import List, Optional, Tuple
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from psycopg2 import pool
from supabase import Client as SupabaseClient  # Import Supabase Client

# Import konfigurasi (jika diperlukan untuk model embedding, dll.)
from ..helper.load_config import TOOLS_CFG


class RAGService:
    """
    Service class for handling Retrieval-Augmented Generation (RAG) operations,
    including PDF processing, embedding generation, and database interactions.
    """

    def __init__(self, db_pool: pool.SimpleConnectionPool, storage_client: SupabaseClient):
        """
        Initializes the RAGService.

        Args:
            db_pool: The psycopg2 connection pool for database operations.
            storage_client: The Supabase client for storage operations.
        """
        if db_pool is None:
            raise ValueError(
                "Database connection pool (db_pool) cannot be None.")
        if storage_client is None:
            raise ValueError(
                "Supabase storage client (storage_client) cannot be None.")
        self.db_pool = db_pool
        self.storage = storage_client
        self.embeddings_model = self._initialize_embeddings()

    def _initialize_embeddings(self) -> Optional[GoogleGenerativeAIEmbeddings]:
        """Initializes the Google Generative AI embeddings model."""
        try:
            # Pastikan API key tersedia
            api_key = TOOLS_CFG.gemini_api_key
            if not api_key:
                st.error("GEMINI_API_KEY not found in configuration/secrets.")
                return None
            return GoogleGenerativeAIEmbeddings(
                model=TOOLS_CFG.rag_embedding_model, google_api_key=api_key
            )
        except Exception as e:
            st.error(f"Failed to initialize embeddings model: {e}")
            return None

    def check_file_exists_in_bucket(self, bucket_name: str, file_name: str) -> bool:
        """Checks if a file already exists in the Supabase Storage bucket."""
        try:
            files_response = self.storage.storage.from_(bucket_name).list()
            if isinstance(files_response, dict) and files_response.get("error"):
                st.error(
                    f"Error listing files in bucket '{bucket_name}': {files_response['error']}")
                return False
            elif isinstance(files_response, list):
                return any(f.get('name') == file_name for f in files_response)
            else:
                st.warning(
                    f"Unknown response format from Supabase list(): {files_response}")
                return False
        except Exception as e:
            st.error(f"Error checking file existence in bucket: {e}")
            return False

    def upload_file_to_supabase(self, file_path: str, bucket_name: str, file_name: str) -> Optional[str]:
        """Uploads a file to Supabase Storage, overwriting if it exists."""
        try:
            with open(file_path, "rb") as file:
                # Use upsert=True to overwrite if the file exists
                response = self.storage.storage.from_(bucket_name).upload(
                    file_name, file, file_options={'upsert': 'true'}
                )
            # Get public URL after successful upload/upsert
            public_url_response = self.storage.storage.from_(
                bucket_name).get_public_url(file_name)

            if isinstance(public_url_response, str):
                st.success(
                    f"File uploaded/updated successfully: {public_url_response}")
                return public_url_response
            elif isinstance(public_url_response, dict) and public_url_response.get("error"):
                st.error(
                    f"Failed to get public URL: {public_url_response['error']}")
                return None
            else:
                st.warning("File uploaded but failed to get public URL.")
                return None
        except Exception as e:
            st.error(f"Error uploading file to Supabase: {e}")
            # Handle specific errors if needed, e.g., duplicate handling if upsert=False
            return None

    def check_file_exists_in_db(self, file_name: str) -> bool:
        """Checks if embeddings for a specific file already exist in the database."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cur:
                # Assuming metadata is TEXT containing JSON
                search_pattern = f'%"file_name": "{file_name}"%'
                cur.execute(
                    "SELECT 1 FROM documents WHERE metadata LIKE %s LIMIT 1", (
                        search_pattern,)
                )
                return cur.fetchone() is not None
        except Exception as e:
            st.error(f"Error checking file existence in DB: {e}")
            return False
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def _load_pdf(self, file_path: str) -> List[Document]:
        """Loads and extracts text from a PDF file."""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            # Add file_name to metadata for each document
            for doc in documents:
                doc.metadata["file_name"] = os.path.basename(file_path)
            return documents
        except Exception as e:
            st.error(f"Error loading PDF '{os.path.basename(file_path)}': {e}")
            return []

    def _split_documents(self, documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
        """Splits documents into smaller chunks."""
        if not documents:
            return []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,  # Explicitly use len
        )
        try:
            return splitter.split_documents(documents)
        except Exception as e:
            st.error(f"Error splitting documents: {e}")
            return []

    def _create_embeddings(self, documents: List[Document]) -> Optional[List[List[float]]]:
        """Generates embeddings for a list of documents."""
        if not self.embeddings_model:
            st.error("Embeddings model not initialized.")
            return None
        if not documents:
            st.warning("No documents provided for embedding.")
            return []
        try:
            st.info(
                f"Creating embeddings for {len(documents)} document chunks...")
            contents = [doc.page_content for doc in documents]
            embeddings = self.embeddings_model.embed_documents(contents)
            st.success("Embeddings created successfully.")
            return embeddings
        except Exception as e:
            st.error(f"Failed to create embeddings: {e}")
            return None

    def _save_embeddings_to_db(self, documents: List[Document], embeddings: List[List[float]], file_name: str):
        """Saves document embeddings to the PostgreSQL database, replacing old ones for the file."""
        if not documents or not embeddings or len(documents) != len(embeddings):
            st.error(
                "Mismatch between documents and embeddings count or empty lists.")
            return False

        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cur:
                # Delete old embeddings for this file first
                st.info(
                    f"Deleting old embeddings for file '{file_name}' (if any)...")
                delete_pattern = f'%"file_name": "{file_name}"%'
                cur.execute(
                    "DELETE FROM documents WHERE metadata LIKE %s", (delete_pattern,))
                st.write(f"Rows deleted: {cur.rowcount}")

                # Insert new embeddings
                st.info(f"Inserting {len(documents)} new embeddings...")
                insert_count = 0
                for doc, embedding in zip(documents, embeddings):
                    embedding_list = embedding if isinstance(
                        embedding, list) else embedding.tolist()
                    embedding_json = json.dumps(embedding_list)
                    metadata_dict = doc.metadata if isinstance(
                        doc.metadata, dict) else {}
                    metadata_json = json.dumps(metadata_dict)
                    cleaned_content = doc.page_content.replace('\x00', '')
                    cleaned_metadata = metadata_json.replace('\x00', '')

                    cur.execute(
                        """
                        INSERT INTO documents (content, metadata, embedding)
                        VALUES (%s, %s, %s::vector)
                        """,
                        (cleaned_content, cleaned_metadata, embedding_json)
                    )
                    insert_count += 1
                conn.commit()
                st.success(
                    f"{insert_count} embeddings saved successfully to the database.")
                return True
        except Exception as e:
            st.error(f"Database error saving embeddings: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rb_e:
                    st.error(f"Rollback failed: {rb_e}")
            return False
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def process_uploaded_pdf(self, uploaded_file, bucket_name: str = "document.rag") -> bool:
        """
        Handles the end-to-end processing of an uploaded PDF file for RAG.
        Uploads to storage, loads, splits, creates embeddings, and saves to DB.

        Args:
            uploaded_file: The file object uploaded via st.file_uploader.
            bucket_name: The name of the Supabase Storage bucket.

        Returns:
            True if processing was successful, False otherwise.
        """
        if uploaded_file is None:
            st.warning("No file uploaded.")
            return False

        file_name = uploaded_file.name
        temp_dir = "temp_pdf_processing"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, file_name)

        try:
            # Save temporarily
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.info(f"Temporary file saved: {temp_file_path}")

            # 1. Check & Upload to Supabase Storage
            if self.check_file_exists_in_bucket(bucket_name, file_name):
                st.warning(
                    f"File '{file_name}' already exists in bucket. Overwriting...")
            else:
                st.info(
                    f"Uploading '{file_name}' to bucket '{bucket_name}'...")

            public_url = self.upload_file_to_supabase(
                temp_file_path, bucket_name, file_name)
            if not public_url:
                st.error("Failed to upload file to Supabase Storage. Aborting.")
                return False
            st.write(f"File URL: {public_url}")

            # 2. Load and Split PDF
            with st.spinner("Loading and splitting PDF..."):
                documents = self._load_pdf(temp_file_path)
                if not documents:
                    return False  # Error handled in _load_pdf
                split_docs = self._split_documents(documents)
                if not split_docs:
                    st.warning("No document chunks generated after splitting.")
                    return False
                st.write(f"Document split into {len(split_docs)} chunks.")

            # 3. Create Embeddings
            embeddings = self._create_embeddings(split_docs)
            if embeddings is None:
                return False  # Error handled in _create_embeddings

            # 4. Save Embeddings to DB
            success = self._save_embeddings_to_db(
                split_docs, embeddings, file_name)
            if success:
                st.success(
                    f"File '{file_name}' processed and embeddings saved successfully!")
            else:
                st.error("Failed to save embeddings to the database.")
            return success

        except Exception as e:
            st.error(
                f"An unexpected error occurred during PDF processing: {e}")
            return False
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e_clean:
                    st.warning(
                        f"Failed to remove temporary file '{temp_file_path}': {e_clean}")

    def display_pdf_preview(self, uploaded_file):
        """Displays a preview of the uploaded PDF."""
        if uploaded_file:
            try:
                base64_pdf = base64.b64encode(
                    uploaded_file.getvalue()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Failed to display PDF preview: {e}")

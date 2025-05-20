# core/__init__.py
import streamlit as st
from .utils.cookies import load_cookie_to_session
from .utils.firebase_config import get_firebase_app
from .utils.database import connect_db

# Import service yang akan diinisialisasi
from .services.UserService import UserService
from .services.UserDataService import UserDataService
from .services.EmailService import EmailService
from .services.RAG import RAGService
from .services.AssetDataService import AssetDataService


def initialize_session_state():
    """Inisialisasi atribut session_state jika belum ada."""
    if "username" not in st.session_state:
        load_cookie_to_session(st.session_state)
    # Inisialisasi Database dan Supabase Storage
    if "db" not in st.session_state or "storage" not in st.session_state:
        try:
            st.session_state.db, st.session_state.storage = connect_db()
            if st.session_state.db is None or st.session_state.storage is None:
                st.error("Inisialisasi DB Pool atau Supabase Storage gagal.")
                st.session_state.db = None
                st.session_state.storage = None
        except Exception as e:
            st.error(
                f"Failed to connect to the database pool or Supabase Storage: {e}")
            st.session_state.db = None
            st.session_state.storage = None

    # Inisialisasi Firebase (Firestore, Auth, firebase_api)
    if "fs" not in st.session_state or "auth" not in st.session_state or "fs_config" not in st.session_state:
        try:
            st.session_state.fs, st.session_state.auth, st.session_state.fs_config = get_firebase_app()
            if st.session_state.fs is None:
                st.error("Inisialisasi Firebase gagal.")
                st.session_state.fs = None
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {e}")
            st.session_state.fs = None

    # Inisialisasi Services (setelah dependensi tersedia)
    services_to_init = ["user_service", "user_data_service", "email_service",
                        "rag_service", "asset_data_service"]  # <-- Tambahkan asset_data_service
    if not all(service in st.session_state for service in services_to_init):
        # Cek dependensi utama
        firebase_ready = "fs" in st.session_state and st.session_state.fs is not None and \
                         "auth" in st.session_state and "fs_config" in st.session_state
        db_ready = "db" in st.session_state and st.session_state.db is not None
        storage_ready = "storage" in st.session_state and st.session_state.storage is not None
        smtp_ready = "smtp" in st.secrets

        if not smtp_ready:
            st.warning(
                "SMTP secrets not found. EmailService cannot be initialized.")
        if not firebase_ready:
            st.warning(
                "Firebase not fully initialized. UserService/UserDataService may not be available.")
        if not db_ready:
            st.warning(
                "Database Pool not initialized. RAGService/AssetDataService may not be available.")
        if not storage_ready:
            st.warning(
                "Supabase Storage not initialized. RAGService may not be available.")

        try:
            # ... (Inisialisasi EmailService, UserDataService, UserService, RAGService tetap sama) ...
            if smtp_ready and "email_service" not in st.session_state:
                # Args lengkap
                st.session_state.email_service = EmailService(smtp_server=st.secrets["smtp"]["server"],
                                                              smtp_port=st.secrets["smtp"]["port"],
                                                              smtp_username=st.secrets["smtp"]["username"],
                                                              smtp_password=st.secrets["smtp"]["password"],)
                print("✅ EmailService initialized.")
            if firebase_ready and "user_data_service" not in st.session_state:
                # Args lengkap
                st.session_state.user_data_service = UserDataService(
                    firestore=st.session_state.fs)
                print("✅ UserDataService initialized.")
            if firebase_ready and "email_service" in st.session_state and "user_service" not in st.session_state:
                # Args lengkap
                st.session_state.user_service = UserService(firestore=st.session_state.fs,
                                                            auth=st.session_state.auth,
                                                            firebase_api=st.session_state.fs_config,
                                                            email_service=st.session_state.email_service)
                print("✅ UserService initialized.")
            if db_ready and storage_ready and "rag_service" not in st.session_state:
                st.session_state.rag_service = RAGService(db_pool=st.session_state.db,
                                                          storage_client=st.session_state.storage)
                print("✅ RAGService initialized.")

            # Inisialisasi AssetDataService (jika DB ready) <-- Tambahkan ini
            if db_ready and "asset_data_service" not in st.session_state:
                st.session_state.asset_data_service = AssetDataService(
                    db_pool=st.session_state.db
                )
                print("✅ AssetDataService initialized.")

        except KeyError as e:
            st.error(
                f"Failed to initialize services: Missing secret key {e}. Check your .streamlit/secrets.toml")
        except ValueError as e:
            st.error(f"Failed to initialize services: {e}")
        except Exception as e:
            st.error(f"Failed to initialize services: {e}")

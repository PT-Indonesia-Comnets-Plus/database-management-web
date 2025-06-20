"""Core module initialization with dependency injection and service management."""

import streamlit as st
import logging
from typing import Optional, Dict, Any
from .utils.session_manager import get_session_manager
from .utils.firebase_config import get_firebase_app
from .utils.database import connect_db

# Import services
from .services.UserService import UserService
from .services.UserDataService import UserDataService
from .services.EmailService import EmailService
from .services.RAG import RAGService
from .services.AssetDataService import AssetDataService

logger = logging.getLogger(__name__)


def initialize_session_state() -> bool:
    """Initialize all session state and services."""
    try:        # ALWAYS attempt to load user session on every initialization (critical for persistence)
        logger.debug("Attempting to load user session...")
        session_manager = get_session_manager()
        session_loaded = session_manager.load_user_session()

        if session_loaded:
            logger.info(
                f"Successfully restored user session: {st.session_state.get('username', 'Unknown')}")
        else:
            logger.debug("No valid user session found, starting fresh session")

        # Initialize Database and Storage
        if "db" not in st.session_state or "storage" not in st.session_state:
            try:
                db_pool, storage = connect_db()
                st.session_state.db = db_pool
                st.session_state.storage = storage
                if db_pool is None:
                    logger.warning("Database connection not available")
                if storage is None:
                    logger.warning("Storage connection not available")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                st.session_state.db = None
                st.session_state.storage = None

        # Initialize Firebase
        if "fs" not in st.session_state or "auth" not in st.session_state or "fs_config" not in st.session_state:
            try:
                firestore, auth, config = get_firebase_app()
                st.session_state.fs = firestore
                st.session_state.auth = auth
                st.session_state.fs_config = config
                if firestore is None:
                    logger.warning("Firebase not available")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                st.session_state.fs = None
                st.session_state.auth = None
                st.session_state.fs_config = None

        # Initialize Services
        services_to_init = ["user_service", "user_data_service",
                            "email_service", "rag_service", "asset_data_service"]

        if not all(service in st.session_state for service in services_to_init):
            # Check dependencies
            firebase_ready = (st.session_state.get("fs") is not None and
                              st.session_state.get("auth") is not None and
                              st.session_state.get("fs_config") is not None)
            db_ready = st.session_state.get("db") is not None
            storage_ready = st.session_state.get("storage") is not None
            smtp_ready = "smtp" in st.secrets

            # Initialize EmailService
            if smtp_ready and "email_service" not in st.session_state:
                try:
                    st.session_state.email_service = EmailService(
                        smtp_server=st.secrets["smtp"]["server"],
                        smtp_port=st.secrets["smtp"]["port"],
                        smtp_username=st.secrets["smtp"]["username"],
                        smtp_password=st.secrets["smtp"]["password"]
                    )
                    logger.info("EmailService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize EmailService: {e}")

            # Initialize UserDataService
            if firebase_ready and "user_data_service" not in st.session_state:
                try:
                    st.session_state.user_data_service = UserDataService(
                        firestore=st.session_state.fs
                    )
                    logger.info("UserDataService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize UserDataService: {e}")

            # Initialize UserService
            if (firebase_ready and
                st.session_state.get("email_service") is not None and
                    "user_service" not in st.session_state):
                try:
                    st.session_state.user_service = UserService(
                        firestore=st.session_state.fs,
                        auth=st.session_state.auth,
                        firebase_api=st.session_state.fs_config,
                        email_service=st.session_state.email_service
                    )
                    logger.info("UserService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize UserService: {e}")

            # Initialize RAGService
            if db_ready and storage_ready and "rag_service" not in st.session_state:
                try:
                    st.session_state.rag_service = RAGService(
                        db_pool=st.session_state.db,
                        storage_client=st.session_state.storage
                    )
                    logger.info("RAGService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize RAGService: {e}")

            # Initialize AssetDataService
            if db_ready and "asset_data_service" not in st.session_state:
                try:
                    st.session_state.asset_data_service = AssetDataService(
                        db_pool=st.session_state.db
                    )
                    logger.info("AssetDataService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize AssetDataService: {e}")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize session state: {e}")
        return False

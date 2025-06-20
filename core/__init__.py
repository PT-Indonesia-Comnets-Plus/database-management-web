"""Core module initialization with dependency injection and service management."""

import streamlit as st
import logging
from typing import Optional, Dict, Any

# Import utilities with error handling
try:
    from .utils.cookies import load_cookie_to_session
    COOKIES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Cookies module not available: {e}")
    COOKIES_AVAILABLE = False
    load_cookie_to_session = None

try:
    from .utils.firebase_config import get_firebase_app
    FIREBASE_CONFIG_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Firebase config not available: {e}")
    FIREBASE_CONFIG_AVAILABLE = False
    get_firebase_app = None

try:
    from .utils.database import connect_db
    DATABASE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Database module not available: {e}")
    DATABASE_AVAILABLE = False
    connect_db = None

# Import services with error handling
try:
    from .services.UserService import UserService
    from .services.UserDataService import UserDataService
    from .services.EmailService import EmailService
    from .services.RAG import RAGService
    from .services.AssetDataService import AssetDataService
    SERVICES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Some services not available: {e}")
    SERVICES_AVAILABLE = False
    UserService = None
    UserDataService = None
    EmailService = None
    RAGService = None
    AssetDataService = None

logger = logging.getLogger(__name__)


def initialize_session_state() -> bool:
    """
    Initialize session state and core services.

    Returns:
        bool: True if initialization successful, False otherwise
    """
    if not SERVICES_AVAILABLE:
        logger.error(
            "Core services not available. Cannot initialize session state.")
        st.error(
            "Application services are not available. Please check your deployment configuration.")
        return False

    try:
        # Load cookies to session state
        if COOKIES_AVAILABLE and load_cookie_to_session:
            load_cookie_to_session()
        else:
            logger.warning("Cookies not available, skipping cookie loading")

        # Initialize services only if not already done
        if 'services_initialized' not in st.session_state:
            if not _initialize_services():
                return False
            st.session_state.services_initialized = True

        return True

    except Exception as e:
        logger.error(f"Failed to initialize session state: {e}")
        st.error(f"Initialization failed: {e}")
        return False


def _initialize_services() -> bool:
    """Initialize all session state and services."""
    try:
        # Initialize Database and Storage
        if DATABASE_AVAILABLE and connect_db:
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
        else:
            logger.warning("Database module not available")
            st.session_state.db = None
            st.session_state.storage = None

        # Initialize Firebase
        if FIREBASE_CONFIG_AVAILABLE and get_firebase_app:
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
        else:
            logger.warning("Firebase config not available")
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
            smtp_ready = hasattr(st, 'secrets') and "smtp" in st.secrets

            # Initialize EmailService
            if smtp_ready and "email_service" not in st.session_state and EmailService:
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
                    st.session_state.email_service = None
            else:
                st.session_state.email_service = None

            # Initialize UserDataService
            if firebase_ready and "user_data_service" not in st.session_state and UserDataService:
                try:
                    st.session_state.user_data_service = UserDataService(
                        firestore=st.session_state.fs
                    )
                    logger.info("UserDataService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize UserDataService: {e}")
                    st.session_state.user_data_service = None
            else:
                st.session_state.user_data_service = None

            # Initialize UserService
            if (firebase_ready and
                st.session_state.get("email_service") is not None and
                    "user_service" not in st.session_state and UserService):
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
                    st.session_state.user_service = None
            else:
                st.session_state.user_service = None

            # Initialize RAGService
            if db_ready and storage_ready and "rag_service" not in st.session_state and RAGService:
                try:
                    st.session_state.rag_service = RAGService(
                        db_pool=st.session_state.db,
                        storage_client=st.session_state.storage
                    )
                    logger.info("RAGService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize RAGService: {e}")
                    st.session_state.rag_service = None
            else:
                st.session_state.rag_service = None

            # Initialize AssetDataService
            if db_ready and "asset_data_service" not in st.session_state and AssetDataService:
                try:
                    st.session_state.asset_data_service = AssetDataService(
                        db_pool=st.session_state.db
                    )
                    logger.info("AssetDataService initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize AssetDataService: {e}")
                    st.session_state.asset_data_service = None
            else:
                st.session_state.asset_data_service = None

        return True

    except Exception as e:
        logger.error(f"Failed to initialize session state: {e}")
        return False

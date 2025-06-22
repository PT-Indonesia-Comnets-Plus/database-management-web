"""Core module initialization with dependency injection and service management."""

import streamlit as st
import logging
from typing import Optional, Dict, Any
from .utils.cookies import load_cookie_to_session
from .utils.firebase_config import get_firebase_app
from .utils.database import connect_db
from .utils.cloud_config import configure_for_cloud, is_streamlit_cloud

# Import services
from .services.UserService import UserService
from .services.UserDataService import UserDataService
from .services.EmailService import EmailService
from .services.RAG import RAGService
from .services.AssetDataService import AssetDataService
from .services.SessionStorageService import get_session_storage_service
from .services.CloudSessionStorage import get_cloud_session_storage

logger = logging.getLogger(__name__)


def initialize_session_state() -> bool:
    """Initialize all session state and services."""
    try:
        # Configure for cloud deployment if needed
        configure_for_cloud()        # Initialize Database and Storage FIRST
        if "db" not in st.session_state or "storage" not in st.session_state:
            try:
                db_pool, storage = connect_db()
                st.session_state.db = db_pool
                st.session_state.storage = storage
                if db_pool is None:
                    logger.error(
                        "Database connection failed - RAG and SQL tools will not function")
                else:
                    logger.info(
                        "Database connection pool created successfully")
                if storage is None:
                    logger.warning("Storage connection not available")
                else:
                    logger.info("Storage connection created successfully")
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

        # Initialize Cloud Session Storage Service (NEW - optimized for Streamlit Cloud)
        if "cloud_session_storage" not in st.session_state:
            try:
                cloud_session_storage = get_cloud_session_storage(
                    db_pool=st.session_state.get("db"),
                    app_prefix="iconnet_app"
                )
                st.session_state.cloud_session_storage = cloud_session_storage
                logger.info(
                    "Cloud session storage service initialized successfully")
            except Exception as e:
                logger.error(
                    f"Failed to initialize cloud session storage service: {e}")
                st.session_state.cloud_session_storage = None

        # Initialize Session Storage Service (Legacy fallback)
        if "session_storage_service" not in st.session_state:
            try:
                session_storage_service = get_session_storage_service(
                    db_pool=st.session_state.get("db"),
                    firestore=st.session_state.get("fs")
                )
                st.session_state.session_storage_service = session_storage_service
                logger.info("Session storage service initialized successfully")
            except Exception as e:
                logger.error(
                    f"Failed to initialize session storage service: {e}")
                # Load user session data (prioritize cloud session storage for production)
                st.session_state.session_storage_service = None
        if "username" not in st.session_state or not st.session_state.get("username"):
            try:
                # First try cloud session storage (optimized for Streamlit Cloud)
                cloud_session_storage = st.session_state.get(
                    "cloud_session_storage")
                if cloud_session_storage:
                    session_data = cloud_session_storage.load_session()
                    if session_data:
                        logger.info(
                            f"User session loaded from cloud storage: {session_data.get('username')}")
                    else:
                        # Try loading by browser fingerprint as fallback
                        session_data = cloud_session_storage.load_session_by_fingerprint()
                        if session_data:
                            logger.info(
                                f"User session restored from fingerprint: {session_data.get('username')}")
                        else:
                            # Fallback to legacy methods
                            load_cookie_to_session(st.session_state)

                            # Then try legacy session storage service
                            session_storage_service = st.session_state.get(
                                "session_storage_service")
                            if session_storage_service:
                                session_data = session_storage_service.load_user_session()
                                if session_data:
                                    logger.info(
                                        f"User session loaded from legacy storage: {session_data.get('username')}")
                else:
                    # Fallback initialization if cloud storage failed
                    load_cookie_to_session(st.session_state)

            except Exception as e:
                logger.error(f"Failed to load user session: {e}")
                # Initialize default session state
                st.session_state.username = ""
                st.session_state.useremail = ""
                st.session_state.role = ""
                st.session_state.signout = True

        # Ensure basic session state variables exist with defaults
        if not hasattr(st.session_state, 'username'):
            st.session_state.username = ""
        if not hasattr(st.session_state, 'useremail'):
            st.session_state.useremail = ""
        if not hasattr(st.session_state, 'role'):
            st.session_state.role = ""
        if not hasattr(st.session_state, 'signout'):
            st.session_state.signout = True

        # Check session timeout after loading session data
        if st.session_state.get('username') and not st.session_state.get('signout', True):
            # Check if session has expired
            import time
            current_time = time.time()
            session_expiry = st.session_state.get('session_expiry')

            if session_expiry and current_time > session_expiry:
                logger.info(
                    f"Session expired for user {st.session_state.get('username')}, clearing session")
                # Clear expired session
                st.session_state.username = ""
                st.session_state.useremail = ""
                st.session_state.role = ""
                st.session_state.signout = True
                if hasattr(st.session_state, 'login_timestamp'):
                    del st.session_state.login_timestamp
                if hasattr(st.session_state, 'session_expiry'):
                    del st.session_state.session_expiry
                # Also clear cookies if available
                try:
                    from core.utils.cookies import clear_user_cookie
                    clear_user_cookie()
                except Exception as e:
                    logger.warning(
                        f"Could not clear cookies on session expiry: {e}")

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

"""Core module initialization with dependency injection and service management."""

import streamlit as st
import logging
import time
from typing import Optional, Dict, Any
from .utils.firebase_config import get_firebase_app
from .utils.database import connect_db

logger = logging.getLogger(__name__)


def initialize_session_state() -> bool:
    """Initialize all session state and services."""
    try:
        # Configure for cloud deployment if needed
        # Initialize Database and Storage FIRST
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
                st.session_state.storage = None        # Initialize Firebase
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
                # Note: PersistentSessionService removed - using cookie manager for persistence# Initialize Cookie Manager for session management
                # Session management is now handled by UserService with database sessions
                st.session_state.fs_config = None
        # No need for cookie manager initialization
        try:
            # Check if we have a valid active session first
            current_user = st.session_state.get("username", "")
            current_signout = st.session_state.get("signout", True)
            current_expiry = st.session_state.get("session_expiry", 0)

            # Only skip loading if we have a valid, non-expired, active session
            skip_loading = (current_user and
                            not current_signout and
                            current_expiry > 0 and
                            current_expiry > time.time())

            if not skip_loading:
                logger.info(
                    "Attempting to restore session from persistent storage...")

                session_loaded = False

                logger.info(
                    "Session restoration is now handled by UserService during app usage")
                session_loaded = True  # Skip old session restoration logic

                # Log final restoration results
                username = st.session_state.get("username", "")
                if username and session_loaded:
                    logger.info(
                        f"🟢 Session restoration successful: {username}")
                elif username:
                    logger.info(
                        f"🟡 Session exists but may need validation: {username}")
                else:
                    logger.info("🔴 No previous session found")
            else:
                logger.info(
                    f"🟢 Valid session already exists for: {current_user}")

        except Exception as e:
            logger.warning(f"Session restoration failed: {e}")
            # Continue without session restoration

        # Ensure basic session state variables exist with defaults
        if "username" not in st.session_state:
            st.session_state.username = ""
        if "useremail" not in st.session_state:
            st.session_state.useremail = ""
        if "role" not in st.session_state:
            st.session_state.role = ""
        if "signout" not in st.session_state:
            st.session_state.signout = True

        # Only check session expiry if user is actually logged in
        username = st.session_state.get('username', '')
        if username and username.strip() and not st.session_state.get('signout', True):
            # Check if session has expired
            from datetime import datetime
            current_time = time.time()
            session_expiry = st.session_state.get('session_expiry')

            if session_expiry:
                # Normalize session_expiry to Unix timestamp for comparison
                try:
                    if isinstance(session_expiry, str):
                        # Convert ISO format string to Unix timestamp
                        session_expiry = datetime.fromisoformat(
                            session_expiry).timestamp()
                        st.session_state.session_expiry = session_expiry  # Store normalized value

                    if current_time > session_expiry:
                        logger.info(
                            f"Session expired for user {username}, clearing session")
                        # Clear expired session
                        st.session_state.username = ""
                        st.session_state.useremail = ""
                        st.session_state.role = ""
                        st.session_state.signout = True
                        if hasattr(st.session_state, 'login_timestamp'):
                            del st.session_state.login_timestamp
                        if hasattr(st.session_state, 'session_expiry'):
                            # Also clear cookies if available
                            del st.session_state.session_expiry
                        try:
                            from core.utils.cookies import clear_cookies
                            clear_cookies()
                        except Exception as e:
                            logger.warning(
                                f"Could not clear cookies on session expiry: {e}")
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid session_expiry format: {session_expiry}, error: {e}")
                    # Clear invalid session
                    st.session_state.signout = True

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
            smtp_ready = "smtp" in st.secrets            # Initialize EmailService
            if smtp_ready and "email_service" not in st.session_state:
                try:
                    from .services.EmailService import EmailService
                    st.session_state.email_service = EmailService(
                        smtp_server=st.secrets["smtp"]["server"],
                        smtp_port=st.secrets["smtp"]["port"],
                        smtp_username=st.secrets["smtp"]["username"],
                        smtp_password=st.secrets["smtp"]["password"]
                    )
                    logger.info("EmailService initialized")
                except Exception as e:
                    # Initialize UserDataService
                    logger.error(f"Failed to initialize EmailService: {e}")
            if firebase_ready and "user_data_service" not in st.session_state:
                try:
                    from .services.UserDataService import UserDataService
                    st.session_state.user_data_service = UserDataService(
                        firestore=st.session_state.fs
                    )
                    logger.info("UserDataService initialized")
                except Exception as e:
                    # Initialize UserService
                    logger.error(f"Failed to initialize UserDataService: {e}")
            if (firebase_ready and
                st.session_state.get("email_service") is not None and
                    "user_service" not in st.session_state):
                try:
                    from .services.UserService import UserService
                    # Get database connection for session management
                    db_connection = st.session_state.get("db")
                    st.session_state.user_service = UserService(
                        firestore=st.session_state.fs,
                        auth=st.session_state.auth,
                        firebase_api=st.session_state.fs_config,
                        email_service=st.session_state.email_service,
                        db_connection=db_connection
                    )
                    logger.info(
                        "UserService initialized with database session support")
                except Exception as e:
                    logger.error(f"Failed to initialize UserService: {e}")
            if db_ready and storage_ready and "rag_service" not in st.session_state:
                try:
                    from .services.RAG import RAGService
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
                    from .services.AssetDataService import AssetDataService
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


# Export the function for external use
__all__ = ['initialize_session_state']

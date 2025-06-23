"""Core module initialization with dependency injection and service management."""

import streamlit as st
import logging
import time
from typing import Optional, Dict, Any
from .utils.cookies import get_cloud_cookie_manager
from .utils.cloud_session_storage import get_cloud_session_storage
from .utils.firebase_config import get_firebase_app
from .utils.database import connect_db
from .utils.cloud_config import configure_for_cloud, is_streamlit_cloud

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
                st.session_state.fs_config = None

        # Initialize Persistent Session Service (NEW)
        if "persistent_session_service" not in st.session_state:
            try:
                from .services.PersistentSessionService import get_persistent_session_service
                st.session_state.persistent_session_service = get_persistent_session_service()
                logger.info("PersistentSessionService initialized")
            except Exception as e:
                logger.error(
                    f"Failed to initialize PersistentSessionService: {e}")
                st.session_state.persistent_session_service = None
        # Initialize Session Storage Service (Legacy fallback)
        st.session_state.cloud_session_storage = None
        if "session_storage_service" not in st.session_state:
            try:
                from .services.SessionStorageService import get_session_storage_service
                session_storage_service = get_session_storage_service(
                    db_pool=st.session_state.get("db"),
                    firestore=st.session_state.get("fs")
                )
                st.session_state.session_storage_service = session_storage_service
                logger.info("Session storage service initialized successfully")
            except Exception as e:
                logger.error(
                    f"Failed to initialize session storage service: {e}")        # Load user session data using cloud-optimized storage
        # ALWAYS attempt to load session, regardless of current session state
        try:
            # Check if we have a valid active session first
            current_user = st.session_state.get("username", "")
            current_signout = st.session_state.get("signout", True)
            # Only skip loading if we have a valid, non-expired, active session
            current_expiry = st.session_state.get("session_expiry", 0)
            skip_loading = (current_user and
                            not current_signout and
                            current_expiry > 0 and
                            current_expiry > time.time())

            if not skip_loading:
                logger.info(
                    "Attempting to restore session from persistent storage...")

                session_loaded = False

                # NEW: Strategy 1 - Try Firestore persistent session first
                if st.session_state.get("persistent_session_service") is not None:
                    try:
                        logger.info(
                            "🔄 Attempting Firestore session restoration...")
                        persistent_service = st.session_state.persistent_session_service

                        # Clean up expired sessions
                        persistent_service.cleanup_expired_sessions()

                        # Try to restore session
                        user_data = persistent_service.restore_session()
                        if user_data:
                            session_loaded = True
                            username = st.session_state.get("username", "")
                            logger.info(
                                f"🟢 Session restored from Firestore for: {username}")
                        else:
                            logger.info("🔄 No valid Firestore session found")
                    except Exception as e:
                        logger.error(
                            f"Firestore session restoration failed: {e}")

                # Strategy 2: Use enhanced cloud session restoration (fallback)
                if not session_loaded:
                    cloud_storage = get_cloud_session_storage()

                    # Try enhanced restoration first (specifically for Streamlit Cloud)
                    try:
                        logger.info("🔄 Trying enhanced session restoration...")
                        session_loaded = cloud_storage._enhanced_session_restoration()
                        if session_loaded:
                            username = st.session_state.get("username", "")
                            logger.info(
                                f"🟢 Session restored via enhanced method: {username}")
                        else:
                            logger.info(
                                "🔄 Enhanced restoration found no valid session")
                            # Fallback to standard restoration
                            session_loaded = cloud_storage.load_user_session()
                            if session_loaded:
                                username = st.session_state.get("username", "")
                                logger.info(
                                    f"🟢 Session restored via standard method: {username}")
                    except Exception as e:
                        logger.error(f"Enhanced restoration failed: {e}")
                        # Enhanced method failed, use standard
                        session_loaded = cloud_storage.load_user_session()

                # Strategy 3: Fallback to cookie manager if cloud storage fails
                if not session_loaded:
                    try:
                        logger.info("Trying cookie manager fallback...")
                        cookie_manager = get_cloud_cookie_manager()
                        session_loaded = cookie_manager.load_user_session()
                        if session_loaded:
                            username = st.session_state.get("username", "")
                            logger.info(
                                f"Session restored via cookies: {username}")
                    except Exception as e:
                        logger.debug(f"Cookie fallback failed: {e}")

                # Strategy 4: Final fallback - check for any session indicators
                if not session_loaded:
                    # Look for any remaining session data in session state
                    for key in list(st.session_state.keys()):
                        if ("user" in key.lower() or "auth" in key.lower() or
                                "login" in key.lower() or "session" in key.lower()):
                            if key not in ["username", "useremail", "role", "signout"]:
                                logger.debug(
                                    f"Found potential session key: {key}")

                    # Check if we have minimal session data
                    username = st.session_state.get("username", "")
                    if username and not st.session_state.get("signout", True):
                        session_loaded = True
                        # Log final restoration results
                        logger.info(
                            f"Minimal session data found for: {username}")

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
                    logger.error(f"Failed to initialize UserDataService: {e}")

            # Initialize UserService
            if (firebase_ready and
                st.session_state.get("email_service") is not None and
                    "user_service" not in st.session_state):
                try:
                    from .services.UserService import UserService
                    st.session_state.user_service = UserService(
                        firestore=st.session_state.fs,
                        auth=st.session_state.auth,
                        firebase_api=st.session_state.fs_config,
                        email_service=st.session_state.email_service
                    )
                    logger.info("UserService initialized")
                except Exception as e:
                    # Initialize RAGService
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

import streamlit as st
import json
import logging

# Try to import firebase modules with fallback
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth
    FIREBASE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Firebase modules not available: {e}")
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    firestore = None
    auth = None

logger = logging.getLogger(__name__)


@st.cache_resource
def get_firebase_app():
    """Initialize Firebase app with error handling for missing configuration."""
    if not FIREBASE_AVAILABLE:
        logger.error(
            "Firebase modules not available. Cannot initialize Firebase.")
        return None, None, None

    try:
        if not firebase_admin._apps:
            # Check if Firebase secrets exist
            if not hasattr(st, 'secrets') or "firebase" not in st.secrets:
                logger.warning(
                    "Firebase secrets not configured. Firebase features will be disabled.")
                return None, None, None

            firebase_key_json = st.secrets["firebase"]["firebase_key_json"]
            key_dict = json.loads(firebase_key_json)

            # Create credentials
            creds = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(creds)

            # Access Firestore and Auth
            logger.info("Firebase app initialized successfully")
        fs = firestore.client()

        # Get Firebase API key from secrets
        firebase_api = st.secrets["firebase"].get("firebase_api", None)
        if not firebase_api:
            logger.warning("Firebase API key not configured")

        return fs, auth, firebase_api

    except (KeyError, AttributeError) as e:
        logger.warning(f"Firebase configuration not available: {e}")
        return None, None, None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid Firebase credentials JSON: {e}")
        return None, None, None
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None, None, None

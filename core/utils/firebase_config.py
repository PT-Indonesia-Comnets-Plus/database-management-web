import firebase_admin
from firebase_admin import credentials, firestore, auth
import streamlit as st
import json
import logging

logger = logging.getLogger(__name__)


@st.cache_resource
def get_firebase_app():
    """Initialize Firebase app with error handling for missing configuration."""
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

            logger.info("Firebase app initialized successfully")

        # Access Firestore and Auth
        fs = firestore.client()
        return fs, auth, firestore

    except (KeyError, AttributeError) as e:
        logger.warning(f"Firebase configuration not available: {e}")
        return None, None, None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid Firebase credentials JSON: {e}")
        return None, None, None
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None, None, None

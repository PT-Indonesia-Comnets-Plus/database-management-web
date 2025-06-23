"""
URL-based Session Token Manager for Streamlit Cloud
This handles session tokens via URL query parameters which persist across refreshes.
"""

import streamlit as st
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class URLSessionManager:
    """Manages session tokens via URL query parameters."""

    @staticmethod
    def set_session_token(token: str) -> None:
        """Set session token in URL query parameters."""
        try:
            # Use only the new Streamlit API (v1.18+)
            if hasattr(st, 'query_params'):
                st.query_params.session_token = token
                logger.info(f"Session token set in URL: {token[:10]}...")
                return
            else:
                logger.warning(
                    "st.query_params not available - URL session not supported")

        except Exception as e:
            logger.error(f"Failed to set session token in URL: {e}")

    @staticmethod
    def get_session_token() -> Optional[str]:
        """Get session token from URL query parameters."""
        try:
            # Use only the new Streamlit API (v1.18+)
            if hasattr(st, 'query_params'):
                token = st.query_params.get('session_token', None)
                if token:
                    logger.info(f"Session token found in URL: {token[:10]}...")
                    return token
                else:
                    logger.debug("No session token found in URL")
                    return None
            else:
                logger.debug("st.query_params not available")
                return None

        except Exception as e:
            logger.error(f"Failed to get session token from URL: {e}")
            return None

    @staticmethod
    def clear_session_token() -> None:
        """Clear session token from URL query parameters."""
        try:
            # Use only the new Streamlit API (v1.18+)
            if hasattr(st, 'query_params'):
                if 'session_token' in st.query_params:
                    del st.query_params['session_token']
                    logger.info("Session token cleared from URL")
                return
            else:
                logger.debug("st.query_params not available")

        except Exception as e:
            logger.error(f"Failed to clear session token from URL: {e}")


def get_url_session_manager() -> URLSessionManager:
    """Get the URL session manager instance."""
    return URLSessionManager()

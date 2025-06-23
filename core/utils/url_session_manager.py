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
            # Try new Streamlit API first (v1.18+)
            if hasattr(st, 'query_params'):
                st.query_params.session_token = token
                logger.info(
                    f"Session token set in URL (new API): {token[:10]}...")
                return

            # Fallback for older Streamlit versions
            try:
                params = {'session_token': token}
                st.experimental_set_query_params(**params)
                logger.info(
                    f"Session token set via experimental API: {token[:10]}...")
                return
            except AttributeError:
                logger.warning("Streamlit query params API not available")
            except Exception as e:
                logger.error(f"Failed to set query params: {e}")

        except Exception as e:
            logger.error(f"Failed to set session token in URL: {e}")

    @staticmethod
    def get_session_token() -> Optional[str]:
        """Get session token from URL query parameters."""
        try:
            # Try new Streamlit API first (v1.18+)
            if hasattr(st, 'query_params'):
                token = st.query_params.get('session_token', None)
                if token:
                    logger.info(
                        f"Session token found in URL (new API): {token[:10]}...")
                    return token

            # Fallback to experimental API
            try:
                query_params = st.experimental_get_query_params()
                if 'session_token' in query_params:
                    token = query_params['session_token'][0]
                    logger.info(
                        f"Session token found via experimental API: {token[:10]}...")
                    return token
            except AttributeError:
                logger.debug("Experimental query params API not available")
            except Exception as e:
                logger.debug(f"Experimental API failed: {e}")

            logger.debug("No session token found in URL")
            return None

        except Exception as e:
            logger.error(f"Failed to get session token from URL: {e}")
            return None

    @staticmethod
    def clear_session_token() -> None:
        """Clear session token from URL query parameters."""
        try:
            # Try new API first
            if hasattr(st, 'query_params'):
                if 'session_token' in st.query_params:
                    del st.query_params['session_token']
                    logger.info("Session token cleared from URL (new API)")
                    return

            # Fallback: set empty query params
            try:
                st.experimental_set_query_params()
                logger.info("Query params cleared via experimental API")
            except AttributeError:
                logger.debug("Experimental query params API not available")
            except Exception as e:
                logger.debug(f"Failed to clear via experimental API: {e}")

        except Exception as e:
            logger.error(f"Failed to clear session token from URL: {e}")


def get_url_session_manager() -> URLSessionManager:
    """Get the URL session manager instance."""
    return URLSessionManager()

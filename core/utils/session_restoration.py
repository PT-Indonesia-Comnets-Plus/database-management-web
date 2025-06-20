"""
Enhanced session restoration utility specifically for persistent login.
This module provides optimized session management that prevents login loops.
"""

import streamlit as st
import logging
from typing import Optional
from .session_manager import get_session_manager

logger = logging.getLogger(__name__)


def ensure_session_persistence() -> bool:
    """
    Ensure user session is properly restored and persistent across page reloads.
    This function should be called early in the application lifecycle.

    Returns:
        bool: True if user session is valid and persistent
    """
    try:
        # Check if we already validated session in this run
        if st.session_state.get('_session_validated', False):
            return st.session_state.get('_session_is_valid', False)

        logger.debug("Validating session persistence...")

        # Get session manager and attempt to restore session
        session_manager = get_session_manager()

        # Try to load user session from any available source
        session_restored = session_manager.load_user_session()

        if session_restored:
            # Validate that the restored session is complete
            username = st.session_state.get('username', '')
            email = st.session_state.get('useremail', '')
            signout = st.session_state.get('signout', True)

            if username and email and not signout:
                st.session_state._session_validated = True
                st.session_state._session_is_valid = True
                logger.info(
                    f"Session persistence validated for user: {username}")
                return True
            else:
                logger.debug("Restored session is incomplete or invalid")

        # No valid session found
        st.session_state._session_validated = True
        st.session_state._session_is_valid = False
        logger.debug("No persistent session found")
        return False

    except Exception as e:
        logger.error(f"Error ensuring session persistence: {e}")
        st.session_state._session_validated = True
        st.session_state._session_is_valid = False
        return False


def clear_session_validation():
    """Clear session validation flags to force re-validation."""
    if '_session_validated' in st.session_state:
        del st.session_state._session_validated
    if '_session_is_valid' in st.session_state:
        del st.session_state._session_is_valid
    logger.debug("Session validation flags cleared")


def is_session_persistent() -> bool:
    """
    Quick check if session is persistent without re-validation.

    Returns:
        bool: True if session has been validated as persistent
    """
    return (st.session_state.get('_session_validated', False) and
            st.session_state.get('_session_is_valid', False))


def debug_session_state():
    """Debug function to log current session state."""
    logger.debug("=== SESSION STATE DEBUG ===")
    logger.debug(f"Username: '{st.session_state.get('username', '')}'")
    logger.debug(f"Email: '{st.session_state.get('useremail', '')}'")
    logger.debug(f"Role: '{st.session_state.get('role', '')}'")
    logger.debug(f"Signout: {st.session_state.get('signout', 'Not set')}")
    logger.debug(
        f"Core initialized: {st.session_state.get('_core_initialized', 'Not set')}")
    logger.debug(
        f"Session validated: {st.session_state.get('_session_validated', 'Not set')}")
    logger.debug(
        f"Session valid: {st.session_state.get('_session_is_valid', 'Not set')}")
    logger.debug("=== END SESSION DEBUG ===")

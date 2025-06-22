"""Session timeout management utilities."""

import streamlit as st
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Session configuration
SESSION_TIMEOUT_HOURS = 7
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_HOURS * 3600


def _is_in_streamlit_context() -> bool:
    """Check if we're running in a proper Streamlit context."""
    try:
        import streamlit.runtime.scriptrunner as sr
        return sr.get_script_run_ctx() is not None
    except (ImportError, AttributeError):
        return True  # Assume we're in context if we can't check


def _safe_session_state_access(key: str, default=None):
    """Safely access session state with context checking."""
    if not _is_in_streamlit_context():
        return default
    return st.session_state.get(key, default)


def _safe_session_state_set(key: str, value):
    """Safely set session state with context checking."""
    if _is_in_streamlit_context():
        st.session_state[key] = value


def _safe_session_state_delete(key: str):
    """Safely delete session state with context checking."""
    if _is_in_streamlit_context() and key in st.session_state:
        del st.session_state[key]


def check_session_timeout() -> bool:
    """
    Check if current session has timed out.

    Returns:
        bool: True if session is valid, False if expired    """
    try:
        # Check if user is logged in
        if _safe_session_state_access('signout', True):
            return False

        if not _safe_session_state_access('username'):
            return False

        # Check session expiry
        current_time = time.time()
        session_expiry = _safe_session_state_access('session_expiry')

        if session_expiry is None:
            # No expiry set - check login timestamp
            login_timestamp = _safe_session_state_access('login_timestamp')
            if login_timestamp is None:
                logger.warning("No session timestamps found - session invalid")
                return False

            # Calculate expiry from login timestamp
            session_expiry = login_timestamp + SESSION_TIMEOUT_SECONDS
            _safe_session_state_set('session_expiry', session_expiry)

        if current_time > session_expiry:
            logger.info(
                f"Session expired for user {_safe_session_state_access('username')} at {datetime.fromtimestamp(session_expiry)}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking session timeout: {e}")
        return False


def logout_if_expired() -> bool:
    """
    Check if session is expired and logout if needed.

    Returns:
        bool: True if session was expired and logout performed, False otherwise    """
    try:
        if not check_session_timeout():
            username = _safe_session_state_access('username', 'Unknown')
            logger.info(f"Session expired for user {username}, logging out")

            # Show expiry message (only if in Streamlit context)
            if _is_in_streamlit_context():
                st.warning(
                    f"⏰ Sesi Anda telah berakhir setelah {SESSION_TIMEOUT_HOURS} jam. Silakan login kembali.")

            # Clear session
            clear_expired_session()
            return True
        return False

    except Exception as e:
        logger.error(f"Error during session expiry check: {e}")
        return False


def clear_expired_session() -> None:
    """Clear expired session data."""
    try:
        # Clear session state
        _safe_session_state_set('username', "")
        _safe_session_state_set('useremail', "")
        _safe_session_state_set('role', "")
        _safe_session_state_set('signout', True)

        # Clear timestamp information
        _safe_session_state_delete('login_timestamp')
        _safe_session_state_delete('session_expiry')

        # Clear cookies if available
        try:
            from core.utils.cookies import clear_user_cookie
            clear_user_cookie()
        except Exception as e:
            logger.warning(f"Could not clear cookies: {e}")

        # Clear other session-related data
        session_keys_to_clear = ['messages', 'thread_id']
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

        logger.info("Expired session cleared successfully")

    except Exception as e:
        logger.error(f"Error clearing expired session: {e}")


def get_session_time_remaining() -> Dict[str, Any]:
    """
    Get information about remaining session time.

    Returns:
        Dict containing session timing information
    """
    try:
        if not check_session_timeout():
            return {
                'is_valid': False,
                'message': 'Session expired or invalid'
            }

        current_time = time.time()
        session_expiry = st.session_state.get('session_expiry')
        login_timestamp = st.session_state.get('login_timestamp')

        if session_expiry and login_timestamp:
            remaining_seconds = session_expiry - current_time
            remaining_hours = remaining_seconds / 3600
            remaining_minutes = remaining_seconds / 60

            login_time = datetime.fromtimestamp(login_timestamp)
            expiry_time = datetime.fromtimestamp(session_expiry)

            return {
                'is_valid': True,
                'username': st.session_state.get('username'),
                'login_time': login_time,
                'expiry_time': expiry_time,
                'remaining_hours': remaining_hours,
                'remaining_minutes': remaining_minutes,
                'remaining_seconds': remaining_seconds,
                'session_timeout_hours': SESSION_TIMEOUT_HOURS,
                'is_warning': remaining_hours < 0.5  # Warning if less than 30 minutes
            }
        else:
            return {
                'is_valid': False,
                'message': 'Session timing information not available'
            }

    except Exception as e:
        logger.error(f"Error getting session time remaining: {e}")
        return {
            'is_valid': False,
            'message': f'Error retrieving session info: {e}'
        }


def display_session_warning() -> None:
    """Display session warning if time is running low."""
    try:
        session_info = get_session_time_remaining()

        if session_info.get('is_valid'):
            remaining_minutes = session_info.get('remaining_minutes', 0)

            if remaining_minutes < 5:
                st.error(
                    f"🚨 Sesi akan berakhir dalam {remaining_minutes:.0f} menit! Simpan pekerjaan Anda.")
            elif remaining_minutes < 15:
                st.warning(
                    f"⚠️ Sesi akan berakhir dalam {remaining_minutes:.0f} menit.")
            elif remaining_minutes < 30:
                st.info(
                    f"ℹ️ Sesi akan berakhir dalam {remaining_minutes:.0f} menit.")

    except Exception as e:
        logger.error(f"Error displaying session warning: {e}")


def ensure_valid_session() -> bool:
    """
    Ensure the current session is valid, redirect to login if not.
    Use this function at the start of protected pages.

    Returns:
        bool: True if session is valid, False otherwise
    """
    try:
        # Check if session is expired
        if logout_if_expired():
            st.stop()  # Stop execution if session expired

        # Check if user is authenticated
        if st.session_state.get('signout', True) or not st.session_state.get('username'):
            st.warning("🔒 Silakan login terlebih dahulu.")
            st.stop()

        return True

    except Exception as e:
        logger.error(f"Error ensuring valid session: {e}")
        return False


def display_session_info_sidebar() -> None:
    """Display compact session info in sidebar."""
    try:
        session_info = get_session_time_remaining()

        if session_info.get('is_valid'):
            remaining_hours = session_info.get('remaining_hours', 0)

            with st.sidebar:
                st.markdown("---")

                if remaining_hours < 0.25:  # Less than 15 minutes
                    remaining_minutes = session_info.get(
                        'remaining_minutes', 0)
                    st.error(f"🚨 Sesi: {remaining_minutes:.0f} menit")
                elif remaining_hours < 0.5:  # Less than 30 minutes
                    remaining_minutes = session_info.get(
                        'remaining_minutes', 0)
                    st.warning(f"⚠️ Sesi: {remaining_minutes:.0f} menit")
                else:
                    st.info(f"⏱️ Sesi: {remaining_hours:.1f} jam")

                # Show login time
                login_time = session_info.get('login_time')
                if login_time:
                    st.caption(f"Login: {login_time.strftime('%H:%M')}")

    except Exception as e:
        logger.error(f"Error displaying session info in sidebar: {e}")


def create_session_timeout_component() -> None:
    """Create a component that shows session timeout warning."""
    try:
        session_info = get_session_time_remaining()

        if session_info.get('is_valid'):
            remaining_minutes = session_info.get('remaining_minutes', 0)

            # Show different types of warnings based on remaining time
            if remaining_minutes < 5:
                st.error(
                    f"🚨 **PERINGATAN:** Sesi akan berakhir dalam {remaining_minutes:.0f} menit! "
                    "Simpan pekerjaan Anda sekarang."
                )
            elif remaining_minutes < 15:
                st.warning(
                    f"⚠️ **Perhatian:** Sesi akan berakhir dalam {remaining_minutes:.0f} menit. "
                    "Pertimbangkan untuk menyimpan pekerjaan Anda."
                )
            elif remaining_minutes < 30:
                with st.expander("ℹ️ Info Sesi", expanded=False):
                    st.info(
                        f"Sesi akan berakhir dalam {remaining_minutes:.0f} menit.")
                    st.write(
                        f"**Login:** {session_info.get('login_time', 'Unknown').strftime('%H:%M %d/%m/%Y')}")
                    st.write(
                        f"**Berakhir:** {session_info.get('expiry_time', 'Unknown').strftime('%H:%M %d/%m/%Y')}")

    except Exception as e:
        logger.error(f"Error creating session timeout component: {e}")

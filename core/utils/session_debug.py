"""
Session debugging helper for Streamlit Cloud deployment.
This file helps debug session persistence issues in cloud environments.
"""

import streamlit as st
import time
import json
from typing import Dict, Any
import logging

from core.utils.cookies import (
    get_session_debug_info,
    is_streamlit_cloud,
    display_session_debug_info
)
from core.utils.persistence_monitor import show_performance_metrics

logger = logging.getLogger(__name__)


def create_session_monitor():
    """Create a session monitoring component for debugging."""
    if not st.secrets.get("debug_mode", False) and is_streamlit_cloud():
        return  # Don't show debug in production cloud

    with st.sidebar:
        with st.expander("🔍 Session Monitor", expanded=False):
            st.write("**Environment:**",
                     "Cloud" if is_streamlit_cloud() else "Local")

            # Session state info
            st.write("**Session State:**")
            session_info = {
                "username": st.session_state.get("username", "None"),
                "useremail": st.session_state.get("useremail", "None"),
                "role": st.session_state.get("role", "None"),
                "signout": st.session_state.get("signout", "None"),
                "login_timestamp": st.session_state.get("login_timestamp", "None"),
                "session_expiry": st.session_state.get("session_expiry", "None"),
            }

            for key, value in session_info.items():
                if key == "session_expiry" and value != "None":
                    try:
                        remaining = float(value) - time.time()
                        st.write(
                            f"- {key}: {remaining/3600:.1f} hours remaining")
                    except:
                        st.write(f"- {key}: {value}")
                else:
                    st.write(f"- {key}: {value}")

            # Cookie status
            st.write("**Cookie Status:**")
            debug_info = get_session_debug_info()
            st.write(
                f"- Cookies Available: {debug_info.get('cookies_available', 'Unknown')}")
            st.write(
                f"- Environment: {debug_info.get('environment', 'Unknown')}")

            if debug_info.get("errors"):
                st.error("Errors detected:")
                for error in debug_info["errors"]:
                    st.write(f"- {error}")

            # Manual actions
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Refresh", key="refresh_session_debug"):
                    st.rerun()

            with col2:
                if st.button("🗑️ Clear Session", key="clear_session_debug"):
                    from core.utils.cookies import clear_cookies
                    clear_cookies()
                    st.success("Session cleared!")
                    st.rerun()


def log_session_event(event_type: str, details: Dict[str, Any] = None):
    """Log session-related events for debugging."""
    try:
        log_data = {
            "timestamp": time.time(),
            "event_type": event_type,
            "environment": "cloud" if is_streamlit_cloud() else "local",
            "session_id": st.session_state.get("username", "anonymous"),
            "details": details or {}
        }

        logger.info(f"Session Event: {json.dumps(log_data, default=str)}")

        # Store recent events in session state for debugging
        if "debug_session_events" not in st.session_state:
            st.session_state.debug_session_events = []

        st.session_state.debug_session_events.append(log_data)

        # Keep only last 10 events
        if len(st.session_state.debug_session_events) > 10:
            st.session_state.debug_session_events = st.session_state.debug_session_events[-10:]

    except Exception as e:
        logger.error(f"Failed to log session event: {e}")


def show_session_events():
    """Display recent session events for debugging."""
    if not st.secrets.get("debug_mode", False) and is_streamlit_cloud():
        return

    events = st.session_state.get("debug_session_events", [])
    if events:
        with st.expander("📝 Recent Session Events", expanded=False):
            for event in reversed(events[-5:]):  # Show last 5 events
                timestamp = time.strftime(
                    "%H:%M:%S", time.localtime(event["timestamp"]))
                st.write(f"**{timestamp}** - {event['event_type']}")
                if event.get("details"):
                    st.json(event["details"])


def test_persistence_methods():
    """Test different persistence methods for debugging."""
    if not st.secrets.get("debug_mode", False) and is_streamlit_cloud():
        return

    with st.expander("🧪 Test Persistence Methods", expanded=False):
        st.write("Test different session persistence methods:")

        test_data = {
            "test_timestamp": time.time(),
            "test_user": "test_user_" + str(int(time.time()))
        }

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Test Cookies"):
                try:
                    from core.utils.cookies import save_user_to_cookie
                    result = save_user_to_cookie(
                        test_data["test_user"],
                        "test@example.com",
                        "user"
                    )
                    st.success(f"Cookie test: {result['method']}")
                    log_session_event("cookie_test", result)
                except Exception as e:
                    st.error(f"Cookie test failed: {e}")

        with col2:
            if st.button("Test Session State"):
                try:
                    st.session_state.test_persistence = test_data
                    st.success("Session state test: OK")
                    log_session_event("session_state_test",
                                      {"status": "success"})
                except Exception as e:
                    st.error(f"Session state test failed: {e}")

        with col3:
            if st.button("Test localStorage"):
                try:
                    js_code = f"""
                    <script>
                    try {{
                        localStorage.setItem('iconnet_test', '{json.dumps(test_data)}');
                        console.log('localStorage test successful');
                    }} catch (e) {{
                        console.error('localStorage test failed:', e);
                    }}
                    </script>
                    """
                    st.components.v1.html(js_code, height=0)
                    st.success("localStorage test executed")
                    log_session_event("localstorage_test", {
                                      "status": "executed"})
                except Exception as e:
                    st.error(f"localStorage test failed: {e}")


def display_cloud_secrets_check():
    """Display status of required secrets for cloud deployment."""
    if not is_streamlit_cloud():
        return

    with st.expander("🔐 Cloud Secrets Status", expanded=False):
        required_secrets = [
            "cookie_password",
            "database.DB_HOST",
            "database.DB_NAME",
            "database.DB_USER",
            "database.DB_PASSWORD",
            "firebase.firebase_key_json",
            "smtp.server",
            "smtp.username",
        ]

        missing_secrets = []
        for secret_path in required_secrets:
            keys = secret_path.split(".")
            current = st.secrets
            try:
                for key in keys:
                    current = current[key]
                st.success(f"✅ {secret_path}")
            except KeyError:
                missing_secrets.append(secret_path)
                st.error(f"❌ {secret_path}")

        if missing_secrets:
            st.error(f"Missing secrets: {missing_secrets}")
            log_session_event("missing_secrets", {"secrets": missing_secrets})
        else:
            st.success("All required secrets are available")


# Main function to add all debugging components
def add_session_debugging():
    """Add all session debugging components to the current page."""
    try:
        create_session_monitor()
        show_session_events()
        test_persistence_methods()
        display_cloud_secrets_check()
        show_performance_metrics()  # Add performance metrics
    except Exception as e:
        logger.error(f"Error in session debugging: {e}")

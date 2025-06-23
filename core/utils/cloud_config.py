"""
Configuration file for Streamlit Cloud deployment.
This file contains cloud-specific configurations and optimizations.
"""

import streamlit as st
import os
import logging

logger = logging.getLogger(__name__)

# Cloud deployment detection


def is_streamlit_cloud() -> bool:
    """Detect if running on Streamlit Cloud with improved detection."""
    # Check environment variables
    env_indicators = [
        os.getenv("STREAMLIT_SHARING_MODE") == "1",
        os.getenv("STREAMLIT_CLOUD_MODE") == "1",
        "streamlit.app" in os.getenv("HOSTNAME", ""),
        "streamlit.app" in os.getenv("SERVER_NAME", ""),
    ]

    # Check if running in cloud environment
    try:
        # Check server address if available
        if hasattr(st, 'get_option'):
            server_address = str(st.get_option("server.address") or "")
            if "streamlit.app" in server_address or "0.0.0.0" in server_address:
                env_indicators.append(True)
    except Exception:
        pass

    # Check if we're in a containerized environment (typical for cloud)
    try:
        path_indicators = [
            "/mount/src/" in os.getcwd(),
            "/app/" in os.getcwd(),
            os.path.exists("/.dockerenv"),
        ]
        env_indicators.extend(path_indicators)
    except Exception:
        pass

    is_cloud = any(env_indicators)
    if is_cloud:
        logger.info("Detected Streamlit Cloud environment")

    return is_cloud


# Session configuration for cloud deployment
CLOUD_SESSION_CONFIG = {
    "session_timeout_hours": 7,  # Changed from days to hours for consistency
    "session_timeout_seconds": 7 * 3600,  # 7 hours in seconds
    "max_sessions_per_user": 3,
    "cleanup_interval_hours": 24,
    "enable_database_fallback": True,
    "enable_js_localStorage": True,
    "enable_stx_cookies": True,
    "enable_legacy_cookies": False,  # Disable for cloud to avoid issues
}

# Cookie settings optimized for Streamlit Cloud
CLOUD_COOKIE_CONFIG = {
    "secure": True,  # HTTPS only
    "samesite": "Strict",
    "httponly": False,  # Allow JS access for localStorage fallback
    "domain": None,  # Let browser set automatically
    "path": "/",
}

# Database connection settings for cloud
CLOUD_DB_CONFIG = {
    "max_connections": 10,
    "connection_timeout": 30,
    "command_timeout": 60,
    "retry_attempts": 3,
    "retry_delay": 1,
}

# Security settings for cloud deployment
CLOUD_SECURITY_CONFIG = {
    "require_https": True,
    "session_encryption": True,
    "csrf_protection": True,
    "rate_limiting": True,
    "max_login_attempts": 5,
    "lockout_duration_minutes": 15,
}


def get_cloud_optimized_secrets():
    """Get cloud-optimized secrets configuration."""
    try:
        # Validate required secrets for cloud deployment
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
            except KeyError:
                missing_secrets.append(secret_path)

        if missing_secrets:
            logger.error(
                f"Missing required secrets for cloud deployment: {missing_secrets}")
            return None

        return {
            "cookie_password": st.secrets.get("cookie_password"),
            "database": {
                "host": st.secrets["database"]["DB_HOST"],
                "name": st.secrets["database"]["DB_NAME"],
                "user": st.secrets["database"]["DB_USER"],
                "password": st.secrets["database"]["DB_PASSWORD"],
                "port": st.secrets["database"].get("DB_PORT", "5432"),
            },
            "firebase": {
                "credentials": st.secrets["firebase"]["firebase_key_json"],
                "api_key": st.secrets.get("firebase_api"),
            },
            "smtp": {
                "server": st.secrets["smtp"]["server"],
                "port": st.secrets["smtp"]["port"],
                "username": st.secrets["smtp"]["username"],
                "password": st.secrets["smtp"]["password"],
            }
        }

    except Exception as e:
        logger.error(f"Error validating cloud secrets: {e}")
        return None


def configure_for_cloud():
    """Configure application optimizations for Streamlit Cloud."""
    if is_streamlit_cloud():
        logger.info("Configuring application for Streamlit Cloud deployment")

        # Set cloud-specific session state flags
        if "is_cloud_deployment" not in st.session_state:
            st.session_state.is_cloud_deployment = True
            st.session_state.cloud_config = CLOUD_SESSION_CONFIG

        # Disable problematic features for cloud
        if "disable_legacy_cookies" not in st.session_state:
            st.session_state.disable_legacy_cookies = True

        # Enable cloud-optimized features
        if "enable_cloud_storage" not in st.session_state:
            st.session_state.enable_cloud_storage = True

        # Configure session timeout for cloud
        if "session_timeout_hours" not in st.session_state:
            st.session_state.session_timeout_hours = CLOUD_SESSION_CONFIG["session_timeout_hours"]
            st.session_state.session_timeout_seconds = CLOUD_SESSION_CONFIG[
                "session_timeout_seconds"]

        return True

    return False


def get_session_timeout_config():
    """Get session timeout configuration based on environment."""
    if is_streamlit_cloud():
        return {
            "timeout_hours": CLOUD_SESSION_CONFIG["session_timeout_hours"],
            "timeout_seconds": CLOUD_SESSION_CONFIG["session_timeout_seconds"],
            "warning_threshold_minutes": 30,
            "critical_threshold_minutes": 5,
        }
    else:
        # Local development settings
        return {
            "timeout_hours": 7,
            "timeout_seconds": 7 * 3600,
            "warning_threshold_minutes": 30,
            "critical_threshold_minutes": 5,
        }


def get_streamlit_cloud_headers():
    """Get headers optimized for Streamlit Cloud."""
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
    }


def create_cloud_secrets_template():
    """Create a template for cloud secrets configuration."""
    template = """
# Streamlit Cloud Secrets Configuration Template
# Copy this to your Streamlit Cloud app's secrets management

[database]
DB_HOST = "your-database-host"
DB_NAME = "your-database-name"
DB_USER = "your-database-user"
DB_PASSWORD = "your-database-password"
DB_PORT = "5432"

[firebase]
firebase_key_json = '''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY\\n-----END PRIVATE KEY-----\\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
}
'''

firebase_api = "your-firebase-api-key"

[smtp]
server = "smtp.gmail.com"
port = 587
username = "your-email@gmail.com"
password = "your-app-password"

# Supabase (if using)
[supabase]
url = "your-supabase-url"
service_role_key = "your-supabase-service-role-key"

# Cookie encryption key (generate a strong random string)
cookie_password = "your-secure-cookie-password-min-32-chars"

# Optional API keys
[gemini]
api_key = "your-gemini-api-key"

[langsmith]
api_key = "your-langsmith-api-key"

[tavily]
api_key = "your-tavily-api-key"
"""
    return template.strip()

"""Database connection management for PostgreSQL and Supabase."""

import psycopg2
from psycopg2 import pool
import streamlit as st
from supabase import create_client
from typing import Tuple, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)


@st.cache_resource
def get_database_config() -> dict:
    """Get database configuration from Streamlit secrets."""
    try:
        # Check if secrets exist
        if not hasattr(st, 'secrets') or "database" not in st.secrets:
            logger.warning(
                "Database secrets not configured. Database features will be disabled.")
            return None

        return {
            'host': st.secrets["database"]["DB_HOST"],
            'database': st.secrets["database"]["DB_NAME"],
            'user': st.secrets["database"]["DB_USER"],
            'password': st.secrets["database"]["DB_PASSWORD"],
            'port': int(st.secrets["database"]["DB_PORT"])
        }
    except (KeyError, AttributeError) as e:
        logger.warning(f"Database configuration not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading database configuration: {e}")
        return None


@st.cache_resource
def get_supabase_config() -> dict:
    """Get Supabase configuration from Streamlit secrets."""
    try:
        # Check if secrets exist
        if not hasattr(st, 'secrets') or "supabase" not in st.secrets:
            logger.warning(
                "Supabase secrets not configured. Supabase features will be disabled.")
            return None

        return {
            'url': st.secrets["supabase"]["url"],
            'key': st.secrets["supabase"]["service_role_key"]
        }
    except (KeyError, AttributeError) as e:
        logger.warning(f"Supabase configuration not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading Supabase configuration: {e}")
        return None


@st.cache_resource
def connect_db() -> Tuple[Optional[pool.SimpleConnectionPool], Optional[object]]:
    """
    Create PostgreSQL connection pool and Supabase client.

    Returns:
        Tuple containing:
        - PostgreSQL connection pool (or None if failed)
        - Supabase client (or None if failed)    """
    db_pool = None
    supabase_client = None

    try:
        # Get configurations
        db_config = get_database_config()
        supabase_config = get_supabase_config()

        # Create PostgreSQL connection pool only if config is available
        if db_config:
            try:
                db_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=5,
                    **db_config
                )

                # Test the connection
                test_conn = db_pool.getconn()
                test_conn.close()
                db_pool.putconn(test_conn)

                logger.info("PostgreSQL connection pool created successfully")
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL connection: {e}")
                db_pool = None
        else:
            logger.info(
                "PostgreSQL configuration not available, skipping database connection")

        # Create Supabase client only if config is available
        if supabase_config:
            try:
                supabase_client = create_client(
                    supabase_config['url'],
                    supabase_config['key']
                )
                logger.info("Supabase client created successfully")
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {e}")
                supabase_client = None
        else:
            logger.info(
                "Supabase configuration not available, skipping Supabase connection")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return None, None
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL connection error: {e}")
        return None, supabase_client
    except Exception as e:
        logger.error(f"Unexpected error during database connection: {e}")
        return None, None

    return db_pool, supabase_client


def close_db_pool(db_pool: pool.SimpleConnectionPool) -> None:
    """
    Safely close the database connection pool.

    Args:
        db_pool: The connection pool to close
    """
    try:
        if db_pool:
            db_pool.closeall()
            logger.info("Database connection pool closed successfully")
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")

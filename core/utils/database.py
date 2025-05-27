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
        return {
            'host': st.secrets["database"]["DB_HOST"],
            'database': st.secrets["database"]["DB_NAME"],
            'user': st.secrets["database"]["DB_USER"],
            'password': st.secrets["database"]["DB_PASSWORD"],
            'port': int(st.secrets["database"]["DB_PORT"])
        }
    except KeyError as e:
        logger.error(f"Missing database configuration: {e}")
        raise ValueError(f"Database configuration incomplete: {e}")


@st.cache_resource
def get_supabase_config() -> dict:
    """Get Supabase configuration from Streamlit secrets."""
    try:
        return {
            'url': st.secrets["supabase"]["url"],
            'key': st.secrets["supabase"]["service_role_key"]
        }
    except KeyError as e:
        logger.error(f"Missing Supabase configuration: {e}")
        raise ValueError(f"Supabase configuration incomplete: {e}")


@st.cache_resource
def connect_db() -> Tuple[Optional[pool.SimpleConnectionPool], Optional[object]]:
    """
    Create PostgreSQL connection pool and Supabase client.

    Returns:
        Tuple containing:
        - PostgreSQL connection pool (or None if failed)
        - Supabase client (or None if failed)
    """
    db_pool = None
    supabase_client = None

    try:
        # Get configurations
        db_config = get_database_config()
        supabase_config = get_supabase_config()

        # Create PostgreSQL connection pool
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

        # Create Supabase client
        supabase_client = create_client(
            supabase_config['url'],
            supabase_config['key']
        )

        logger.info("Supabase client created successfully")

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

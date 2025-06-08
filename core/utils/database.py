"""Database connection management for PostgreSQL and Supabase."""

import psycopg2
from psycopg2 import pool, OperationalError, InterfaceError
import streamlit as st
from supabase import create_client
from typing import Tuple, Optional, Callable, Any
import logging
import time
import functools
import hashlib
import pickle
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_CONFIG = {
    'asset_data_ttl': 3600,  # 1 hour for asset data
    'schema_ttl': 7200,      # 2 hours for schema data
    'aggregation_ttl': 1800,  # 30 minutes for aggregations
    'map_data_ttl': 1800,    # 30 minutes for map data
    'max_cache_size': 100    # Maximum number of cached items
}

# In-memory cache storage
_cache_storage = {}


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a unique cache key based on function arguments."""
    key_data = f"{args}_{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()


def is_cache_valid(timestamp: datetime, ttl_seconds: int) -> bool:
    """Check if cached data is still valid based on TTL."""
    return datetime.now() - timestamp < timedelta(seconds=ttl_seconds)


def get_from_cache(cache_key: str, ttl_seconds: int) -> Optional[Any]:
    """Retrieve data from cache if valid."""
    if cache_key in _cache_storage:
        cached_item = _cache_storage[cache_key]
        if is_cache_valid(cached_item['timestamp'], ttl_seconds):
            logger.info(f"Cache HIT for key: {cache_key[:8]}...")
            return cached_item['data']
        else:
            # Remove expired cache
            logger.info(f"Cache EXPIRED for key: {cache_key[:8]}...")
            del _cache_storage[cache_key]

    logger.info(f"Cache MISS for key: {cache_key[:8]}...")
    return None


def set_cache(cache_key: str, data: Any) -> None:
    """Store data in cache with timestamp."""
    # Implement LRU eviction if cache is full
    if len(_cache_storage) >= CACHE_CONFIG['max_cache_size']:
        # Remove oldest cache entry
        oldest_key = min(_cache_storage.keys(),
                         key=lambda k: _cache_storage[k]['timestamp'])
        del _cache_storage[oldest_key]
        logger.info(f"Cache evicted oldest entry: {oldest_key[:8]}...")

    _cache_storage[cache_key] = {
        'data': data,
        'timestamp': datetime.now(),
        'size': len(pickle.dumps(data)) if hasattr(data, '__len__') else 0
    }
    logger.info(f"Cache SET for key: {cache_key[:8]}...")


def clear_cache(pattern: Optional[str] = None) -> None:
    """Clear cache entries matching pattern, or all if pattern is None."""
    if pattern is None:
        _cache_storage.clear()
        logger.info("All cache cleared")
    else:
        keys_to_remove = [k for k in _cache_storage.keys() if pattern in k]
        for key in keys_to_remove:
            del _cache_storage[key]
        logger.info(f"Cache cleared for pattern: {pattern}")


def cache_query_result(ttl_seconds: int = 3600):
    """Decorator for caching database query results."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = generate_cache_key(func.__name__, *args, **kwargs)

            # Try to get from cache
            cached_result = get_from_cache(cache_key, ttl_seconds)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                set_cache(cache_key, result)

            return result
        return wrapper
    return decorator


@st.cache_resource(ttl=CACHE_CONFIG['schema_ttl'])
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
        # Create PostgreSQL connection pool only if config is available
        supabase_config = get_supabase_config()
        if db_config:
            try:                # Create enhanced db_config with timeout parameters
                enhanced_db_config = {
                    **db_config,
                    'connect_timeout': 10,
                    'options': '-c statement_timeout=30000'  # 30 second query timeout
                }

                db_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=5,
                    **enhanced_db_config
                )

                # Test the connection with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        test_conn = db_pool.getconn()
                        if test_conn.closed != 0:
                            raise OperationalError("Connection is closed")

                        # Test with a simple query
                        with test_conn.cursor() as cur:
                            cur.execute("SELECT 1")
                            cur.fetchone()

                        db_pool.putconn(test_conn)
                        break
                    except (OperationalError, InterfaceError) as e:
                        logger.warning(
                            f"Connection test attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(2 ** attempt)  # Exponential backoff

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


def is_connection_alive(connection) -> bool:
    """
    Check if a database connection is still alive.

    Args:
        connection: The database connection to test

    Returns:
        bool: True if connection is alive, False otherwise
    """
    try:
        if connection.closed != 0:
            return False

        # Test with a simple query
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except (OperationalError, InterfaceError, AttributeError):
        return False


def get_robust_connection(db_pool: pool.SimpleConnectionPool, max_retries: int = 3):
    """
    Get a robust database connection with retry logic.

    Args:
        db_pool: The connection pool
        max_retries: Maximum number of retry attempts

    Returns:
        A valid database connection

    Raises:
        OperationalError: If unable to get a valid connection after retries
    """
    for attempt in range(max_retries):
        try:
            conn = db_pool.getconn()

            # Test if connection is alive
            if is_connection_alive(conn):
                return conn
            else:
                # Connection is dead, discard it and try again
                logger.warning(
                    f"Dead connection detected on attempt {attempt + 1}, discarding...")
                try:
                    # Force close the bad connection
                    db_pool.putconn(conn, close=True)
                except:
                    pass

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise OperationalError(
                        "Unable to get alive connection after retries")

        except (OperationalError, InterfaceError) as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                raise

    raise OperationalError("Unable to get connection after all retries")


def execute_with_retry(db_pool: pool.SimpleConnectionPool,
                       operation: Callable[[Any], Any],
                       max_retries: int = 3) -> Any:
    """
    Execute a database operation with retry logic for connection failures.

    Args:
        db_pool: The connection pool
        operation: A callable that takes a connection and returns a result
        max_retries: Maximum number of retry attempts

    Returns:
        The result of the operation

    Raises:
        Exception: The last exception encountered if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_robust_connection(db_pool, max_retries=2)
            result = operation(conn)
            return result

        except (OperationalError, InterfaceError) as e:
            last_exception = e
            logger.warning(
                f"Database operation attempt {attempt + 1} failed: {e}")

            # Close the problematic connection
            if conn:
                try:
                    db_pool.putconn(conn, close=True)
                    conn = None
                except:
                    pass

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                break

        except Exception as e:
            # Non-connection related errors should not be retried
            last_exception = e
            break

        finally:
            # Return connection to pool if still valid
            if conn:
                try:
                    db_pool.putconn(conn)
                except:
                    pass

    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    else:
        raise OperationalError("Database operation failed after all retries")

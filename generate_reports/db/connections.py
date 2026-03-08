import psycopg2
import psycopg2.extras
from psycopg2 import pool

from generate_reports.config import DATABASE_URL

# ── Single pool instance shared across the app ──
_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return _pool


def get_conn():
    """Borrow a connection from the pool."""
    return get_pool().getconn()


def release_conn(conn):
    """Return a connection back to the pool."""
    get_pool().putconn(conn)

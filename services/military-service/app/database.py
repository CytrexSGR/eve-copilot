"""Database connections for military-service."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Primary military DB
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "eve_db"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "military_db"),
    "user": os.getenv("POSTGRES_USER", "eve"),
    "password": os.getenv("POSTGRES_PASSWORD", "eve"),
}

# SDE DB (read-only, for invTypes/invGroups/mapSolarSystems)
SDE_DB_CONFIG = {
    "host": os.getenv("SDE_POSTGRES_HOST", os.getenv("POSTGRES_HOST", "eve_db")),
    "port": int(os.getenv("SDE_POSTGRES_PORT", os.getenv("POSTGRES_PORT", "5432"))),
    "dbname": os.getenv("SDE_POSTGRES_DB", os.getenv("POSTGRES_DB", "eve_copilot")),
    "user": os.getenv("SDE_POSTGRES_USER", os.getenv("POSTGRES_USER", "eve")),
    "password": os.getenv("SDE_POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", "eve")),
}

def get_db():
    """Get primary military DB connection."""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

def get_sde_db():
    """Get SDE DB connection (read-only)."""
    conn = psycopg2.connect(**SDE_DB_CONFIG, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

@contextmanager
def db_cursor():
    """Context manager for military DB cursor."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()

@contextmanager
def sde_cursor():
    """Context manager for SDE DB cursor (read-only)."""
    conn = get_sde_db()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()

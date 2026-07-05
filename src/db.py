"""
Shared database connection for the profitability diagnostics project.

Reads the same DATABASE_URL environment variable used in Next Steps #5:

    $env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/profitability_diagnostics"

Both src/dashboard.py and src/simulate.py import get_engine() from here so
there is exactly one place that knows how to connect.
"""

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

DEFAULT_DB_URL = "postgresql+psycopg://postgres@localhost:5432/profitability_diagnostics"

_engine: Engine | None = None


import os

def get_database_url():
    url = os.getenv("DATABASE_URL")

    # DEV fallback
    if not url:
        return None

    return url


def get_engine():
    global _engine

    if _engine is not None:
        return _engine

    url = get_database_url()

    if url is None:
        return None  # important: allow fallback mode

    _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def check_connection() -> bool:
    """Quick connectivity check. Returns True/False, prints a helpful message on failure."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception as exc:  # noqa: BLE001 - surface any connection problem to the user
        print(f"Could not connect to the database: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if check_connection():
        print("Connection OK.")
    else:
        sys.exit(1)

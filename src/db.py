import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None



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

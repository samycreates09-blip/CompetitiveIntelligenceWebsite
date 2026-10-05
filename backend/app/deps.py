from collections.abc import Generator

from sqlalchemy import Connection

from app.database import engine


def get_db() -> Generator[Connection, None, None]:
    with engine.connect() as conn:
        yield conn


def get_write_db() -> Generator[Connection, None, None]:
    """Atomic transaction dependency reserved for explicit observation submissions."""
    with engine.begin() as conn:
        yield conn

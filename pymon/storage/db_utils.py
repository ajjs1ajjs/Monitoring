"""Database utility functions"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator


def get_db_path() -> str:
    return os.getenv("DB_PATH", "pymon.db")


@contextmanager
def get_db():
    """Context manager for SQLite connections - ensures proper cleanup"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
import os

from pymon.storage.backend import MemoryStorage, SQLiteStorage, StorageBackend

storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global storage
    if storage is None:
        # Default to SQLite if nothing initialized
        db_path = os.getenv("DB_PATH", "pymon.db")
        storage = SQLiteStorage(db_path=db_path)
    return storage


def init_storage(backend: str = "sqlite", db_path: str = "pymon.db", **kwargs) -> StorageBackend:
    global storage
    if backend == "sqlite":
        storage = SQLiteStorage(db_path=db_path)
    else:
        # Fallback to memory for tests or ephemeral runs
        storage = MemoryStorage()
    return storage

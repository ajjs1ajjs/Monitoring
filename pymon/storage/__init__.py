import os
from pymon.storage.backend import MemoryStorage, SQLiteStorage, StorageBackend

try:
    from pymon.storage.postgres import PostgresStorage
except Exception:
    PostgresStorage = None

storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global storage
    if storage is None:
        storage = MemoryStorage()
    return storage


def init_storage(backend: str = "memory", db_path: str = "pymon.db", **kwargs) -> StorageBackend:
    global storage
    if backend == "sqlite":
        storage = SQLiteStorage(db_path=db_path)
    elif backend == "postgres" and PostgresStorage is not None:
        dsn = kwargs.get("dsn") or os.getenv("PG_DSN", "postgresql://user:password@localhost/pymon")
        storage = PostgresStorage(dsn=dsn)
    else:
        storage = MemoryStorage()
    return storage
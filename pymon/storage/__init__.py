from pymon.storage.backend import MemoryStorage, SQLiteStorage, StorageBackend

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
    else:
        storage = MemoryStorage()
    return storage

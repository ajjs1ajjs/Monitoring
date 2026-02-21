"""Time-series storage backend"""

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from pymon.metrics.models import Metric


@dataclass
class DataPoint:
    timestamp: datetime
    value: float


class StorageBackend(ABC):
    @abstractmethod
    async def write(self, metric: Metric) -> None:
        pass

    @abstractmethod
    async def read(
        self,
        name: str,
        start: datetime,
        end: datetime,
        labels: dict[str, str] | None = None,
        step: int = 60,
    ) -> list[DataPoint]:
        pass

    @abstractmethod
    async def get_series_names(self) -> list[str]:
        pass


class MemoryStorage(StorageBackend):
    def __init__(self, retention_hours: int = 24):
        self._data: dict[str, list[DataPoint]] = defaultdict(list)
        self._retention = timedelta(hours=retention_hours)
        self._lock = asyncio.Lock()

    async def write(self, metric: Metric) -> None:
        async with self._lock:
            key = f"{metric.name}:{metric.labels_key}"
            self._data[key].append(DataPoint(timestamp=metric.timestamp, value=metric.value))
            await self._cleanup(key)

    async def _cleanup(self, key: str) -> None:
        cutoff = datetime.now(timezone.utc) - self._retention
        self._data[key] = [dp for dp in self._data[key] if dp.timestamp > cutoff]

    async def read(
        self,
        name: str,
        start: datetime,
        end: datetime,
        labels: dict[str, str] | None = None,
        step: int = 60,
    ) -> list[DataPoint]:
        key_prefix = f"{name}:"
        result = []

        async with self._lock:
            for key, points in self._data.items():
                if not key.startswith(key_prefix):
                    continue

                if labels:
                    continue

                for point in points:
                    if start <= point.timestamp <= end:
                        result.append(point)

        return result

    async def get_series_names(self) -> list[str]:
        async with self._lock:
            return list(set(key.split(":")[0] for key in self._data.keys()))


class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: str = "pymon.db"):
        self._db_path = db_path
        self._initialized = False

    async def _init_db(self) -> None:
        if self._initialized:
            return

        import aiosqlite

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    labels TEXT,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
            await db.commit()

        self._initialized = True

    async def write(self, metric: Metric) -> None:
        await self._init_db()
        import aiosqlite

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO metrics (name, labels, value, timestamp) VALUES (?, ?, ?, ?)",
                (metric.name, metric.labels_key, metric.value, metric.timestamp.isoformat()),
            )
            await db.commit()

    async def read(
        self,
        name: str,
        start: datetime,
        end: datetime,
        labels: dict[str, str] | None = None,
        step: int = 60,
    ) -> list[DataPoint]:
        await self._init_db()
        import aiosqlite

        result = []
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT timestamp, value FROM metrics WHERE name = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
                (name, start.isoformat(), end.isoformat()),
            ) as cursor:
                async for row in cursor:
                    result.append(DataPoint(timestamp=datetime.fromisoformat(row[0]), value=row[1]))
        return result

    async def get_series_names(self) -> list[str]:
        await self._init_db()
        import aiosqlite

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT DISTINCT name FROM metrics") as cursor:
                return [row[0] async for row in cursor]

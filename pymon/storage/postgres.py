"""PostgreSQL storage backend (async) for PyMon"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List

import asyncpg

from .backend import StorageBackend, DataPoint
from pymon.metrics.models import Label, MetricType
from pymon.metrics import models as metrics_models


class PostgresStorage(StorageBackend):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.pool.Pool | None = None
        self._initialized = False

    async def _init(self) -> None:
        if self._initialized:
            return
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._dsn)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS metrics (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        labels TEXT,
                        value REAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL
                    )
                    """
                )
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
        self._initialized = True

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._initialized = False

    async def write(self, metric: metrics_models.Metric) -> None:
        await self._init()
        async with self._pool.acquire() as conn:
            # store labels as JSON string for simplicity
            await conn.execute(
                "INSERT INTO metrics (name, labels, value, timestamp) VALUES ($1, $2, $3, $4)",
                metric.name,
                metric.labels_key,
                metric.value,
                metric.timestamp.isoformat(),
            )

    async def read(self, name: str, start, end, labels=None, step: int = 60) -> List[DataPoint]:
        await self._init()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT timestamp, value FROM metrics WHERE name = $1 AND timestamp BETWEEN $2 AND $3 ORDER BY timestamp",
                name,
                start.isoformat(),
                end.isoformat(),
            )
            result: List[DataPoint] = []
            for r in rows:
                ts = datetime.fromisoformat(r["timestamp"]) if isinstance(r["timestamp"], str) else r["timestamp"]
                if not isinstance(ts, datetime):
                    ts = datetime.now(timezone.utc)
                result.append(DataPoint(timestamp=ts, value=float(r["value"])))
            return result

    async def get_series_names(self) -> List[str]:
        await self._init()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT name FROM metrics")
            return [r["name"] for r in rows]

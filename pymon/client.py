"""HTTP client for pushing metrics to PyMon server"""

import asyncio
from typing import Any

import httpx

from pymon.metrics.models import MetricType


class PyMonClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=10.0)
        self._token: str | None = None

    async def login(self, username: str, password: str) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        return data

    async def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def push(
        self,
        name: str,
        value: float,
        metric_type: str = "gauge",
        labels: dict[str, str] | None = None,
        help_text: str = "",
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "value": value,
            "type": metric_type,
            "labels": [{"name": k, "value": v} for k, v in (labels or {}).items()],
            "help_text": help_text,
        }

        resp = await self._client.post(f"{self.base_url}/api/v1/metrics", json=payload, headers=await self._headers())
        resp.raise_for_status()
        return resp.json()

    async def query(
        self, query: str, start: str | None = None, end: str | None = None, step: int = 60, hours: int | None = None
    ) -> list[dict]:
        from datetime import datetime, timedelta

        params = {"query": query, "step": step}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if hours and not start:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=hours)
            params["start"] = start_dt.isoformat()
            params["end"] = end_dt.isoformat()

        resp = await self._client.get(f"{self.base_url}/api/v1/query", params=params, headers=await self._headers())
        resp.raise_for_status()
        return resp.json().get("result", [])

    async def list_series(self) -> list[str]:
        resp = await self._client.get(f"{self.base_url}/api/v1/series", headers=await self._headers())
        resp.raise_for_status()
        return resp.json().get("series", [])

    async def get_metrics(self) -> list[dict]:
        resp = await self._client.get(f"{self.base_url}/api/v1/metrics", headers=await self._headers())
        resp.raise_for_status()
        return resp.json().get("metrics", [])

    async def create_api_key(self, name: str) -> str:
        resp = await self._client.post(
            f"{self.base_url}/api/v1/auth/api-keys",
            json={"name": name},
            headers=await self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["api_key"]

    async def list_api_keys(self) -> list[dict]:
        resp = await self._client.get(f"{self.base_url}/api/v1/auth/api-keys", headers=await self._headers())
        resp.raise_for_status()
        return resp.json().get("api_keys", [])

    async def delete_api_key(self, key_id: int) -> bool:
        resp = await self._client.delete(
            f"{self.base_url}/api/v1/auth/api-keys/{key_id}",
            headers=await self._headers(),
        )
        return resp.status_code == 200

    async def health(self) -> dict:
        resp = await self._client.get(f"{self.base_url}/api/v1/health")
        resp.raise_for_status()
        return resp.json()

    async def prometheus_export(self) -> str:
        resp = await self._client.get(f"{self.base_url}/metrics")
        resp.raise_for_status()
        return resp.text

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "PyMonClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


def push_metric(
    url: str, name: str, value: float, labels: dict[str, str] | None = None, metric_type: str = "gauge"
) -> None:
    async def _push():
        async with PyMonClient(url) as client:
            await client.push(name, value, metric_type, labels)

    asyncio.run(_push())

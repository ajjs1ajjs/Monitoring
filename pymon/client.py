"""HTTP client for pushing metrics to PyMon server"""

import asyncio
from typing import Any, cast

import httpx


class PyMonClient:
    def __init__(self, base_url: str = "http://localhost:10000"):
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
        return cast(dict[str, Any], data)

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
        return cast(dict[str, Any], resp.json())

    async def get_metrics(self) -> list[dict]:
        resp = await self._client.get(f"{self.base_url}/api/v1/metrics", headers=await self._headers())
        resp.raise_for_status()
        return cast(list[dict], resp.json().get("metrics", []))

    async def get_server_history(self, server_id: int, range: str = "1h") -> dict:
        resp = await self._client.get(
            f"{self.base_url}/api/v1/servers/{server_id}/history",
            params={"range": range},
            headers=await self._headers(),
        )
        resp.raise_for_status()
        return cast(dict, resp.json())

    async def create_api_key(self, name: str) -> str:
        resp = await self._client.post(
            f"{self.base_url}/api/v1/auth/api-keys",
            json={"name": name},
            headers=await self._headers(),
        )
        resp.raise_for_status()
        return cast(str, resp.json()["api_key"])

    async def list_api_keys(self) -> list[dict]:
        resp = await self._client.get(f"{self.base_url}/api/v1/auth/api-keys", headers=await self._headers())
        resp.raise_for_status()
        return cast(list[dict], resp.json().get("api_keys", []))

    async def delete_api_key(self, key_id: int) -> bool:
        resp = await self._client.delete(
            f"{self.base_url}/api/v1/auth/api-keys/{key_id}",
            headers=await self._headers(),
        )
        return resp.status_code == 200

    async def health(self) -> dict:
        resp = await self._client.get(f"{self.base_url}/api/v1/health")
        resp.raise_for_status()
        return cast(dict, resp.json())

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
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(_push_async(url, name, value, labels, metric_type))
            return
    except RuntimeError:
        pass
    asyncio.run(_push_async(url, name, value, labels, metric_type))


async def _push_async(
    url: str, name: str, value: float, labels: dict[str, str] | None = None, metric_type: str = "gauge"
) -> None:
    async with PyMonClient(url) as client:
        await client.push(name, value, metric_type, labels)

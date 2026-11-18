import logging
from typing import Any

import httpx

from app.integration.adapters.base import ExternalSystemAdapter
from app.integration.config import SystemConnector

logger = logging.getLogger("delv-sog.integration")


class HttpAdapterMixin:
    connector: SystemConnector

    @property
    def _http_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.connector.api_key:
            headers["Authorization"] = f"Bearer {self.connector.api_key}"
        return headers

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self.connector.base_url.rstrip("/") + path
        timeout = httpx.Timeout(self.connector.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=self._http_headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        url = self.connector.base_url.rstrip("/") + path
        timeout = httpx.Timeout(self.connector.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=self._http_headers, json=data)
            resp.raise_for_status()
            return resp.json()


class BaseHttpAdapter(HttpAdapterMixin, ExternalSystemAdapter):
    def __init__(self, connector: SystemConnector):
        self.connector = connector

    async def test_connection(self) -> dict[str, Any]:
        try:
            data = await self._get("/health")
            return {"ok": True, "detail": data}
        except Exception as e:
            return {"ok": False, "error": str(e)}
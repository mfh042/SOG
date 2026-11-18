from typing import Any

from app.integration.adapters.base import (
    ExternalSystemAdapter,
    RemoteMaterial,
    RemoteOrder,
    RemoteBom,
    RemoteInventory,
    RemoteCustomer,
)


class LocalModeAdapter(ExternalSystemAdapter):
    system_name = "LOCAL"

    async def test_connection(self) -> dict[str, Any]:
        return {"ok": True, "mode": "local", "message": "独立运行模式，使用本地数据"}

    async def fetch_orders(self, since: str | None = None) -> list[RemoteOrder]:
        return []

    async def fetch_materials(self, since: str | None = None) -> list[RemoteMaterial]:
        return []

    async def fetch_boms(self, since: str | None = None) -> list[RemoteBom]:
        return []

    async def fetch_inventory(self, since: str | None = None) -> list[RemoteInventory]:
        return []

    async def fetch_customers(self, since: str | None = None) -> list[RemoteCustomer]:
        return []
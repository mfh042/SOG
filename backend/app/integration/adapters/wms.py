from app.integration.adapters.base import RemoteInventory
from app.integration.adapters.http_base import BaseHttpAdapter
from app.integration.config import SystemConnector


class GenericWmsAdapter(BaseHttpAdapter):
    system_name = "WMS"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)

    async def fetch_inventory(self, since: str | None = None) -> list[RemoteInventory]:
        params = {"since": since} if since else None
        data = await self._get("/api/inventory", params=params)
        results = []
        for row in data.get("items", data if isinstance(data, list) else []):
            results.append(RemoteInventory(
                external_id=str(row.get("id", "")),
                material_code=row.get("material_code", ""),
                batch_no=row.get("batch_no", ""),
                location=row.get("location", ""),
                qty_on_hand=float(row.get("qty_on_hand", 0)),
                qty_reserved=float(row.get("qty_reserved", 0)),
            ))
        return results
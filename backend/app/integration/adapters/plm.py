from app.integration.adapters.base import RemoteBom, RemoteBomItem
from app.integration.adapters.http_base import BaseHttpAdapter
from app.integration.config import SystemConnector


class GenericPlmAdapter(BaseHttpAdapter):
    system_name = "PLM"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)

    async def fetch_boms(self, since: str | None = None) -> list[RemoteBom]:
        params = {"since": since} if since else None
        data = await self._get("/api/boms", params=params)
        results = []
        for row in data.get("items", data if isinstance(data, list) else []):
            items = [
                RemoteBomItem(
                    external_id=str(it.get("id", "")),
                    component_code=it.get("component_code", ""),
                    component_name=it.get("component_name", ""),
                    qty=float(it.get("qty", 1)),
                    loss_rate=float(it.get("loss_rate", 0)),
                    seq=int(it.get("seq", 1)),
                )
                for it in row.get("items", [])
            ]
            results.append(RemoteBom(
                external_id=str(row.get("id", "")),
                product_code=row.get("product_code", ""),
                version=row.get("version", "V1"),
                is_active=bool(row.get("is_active", True)),
                items=items,
            ))
        return results
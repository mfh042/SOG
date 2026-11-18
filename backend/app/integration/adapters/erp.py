from app.integration.adapters.base import RemoteMaterial, RemoteOrder, RemoteOrderItem
from app.integration.adapters.http_base import BaseHttpAdapter
from app.integration.config import SystemConnector


class GenericErpAdapter(BaseHttpAdapter):
    system_name = "ERP"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)

    async def fetch_orders(self, since: str | None = None) -> list[RemoteOrder]:
        params = {"since": since} if since else None
        data = await self._get("/api/orders", params=params)
        results = []
        for row in data.get("items", data if isinstance(data, list) else []):
            items = [
                RemoteOrderItem(
                    external_id=str(it.get("id", "")),
                    line_no=int(it.get("line_no", 1)),
                    material_code=it.get("material_code", ""),
                    material_name=it.get("material_name", ""),
                    spec=it.get("spec", ""),
                    qty=float(it.get("qty", 0)),
                    unit=it.get("unit", "PCS"),
                )
                for it in row.get("items", [])
            ]
            results.append(RemoteOrder(
                external_id=str(row.get("id", row.get("order_no", ""))),
                order_no=row.get("order_no", ""),
                customer_name=row.get("customer_name", ""),
                product_model=row.get("product_model", ""),
                priority=int(row.get("priority", 3)),
                planned_date=str(row.get("planned_date", "")),
                note=row.get("note", ""),
                items=items,
            ))
        return results

    async def fetch_materials(self, since: str | None = None) -> list[RemoteMaterial]:
        params = {"since": since} if since else None
        data = await self._get("/api/materials", params=params)
        results = []
        for row in data.get("items", data if isinstance(data, list) else []):
            results.append(RemoteMaterial(
                external_id=str(row.get("id", "")),
                code=row.get("code", ""),
                name=row.get("name", ""),
                type=row.get("type", "RAW"),
                spec=row.get("spec", ""),
                unit=row.get("unit", "PCS"),
            ))
        return results
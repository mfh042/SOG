"""SAP S/4HANA OData 适配器。

SAP S/4HANA 通过 OData V2/V4 暴露主数据和业务单据，
常见服务端点：
  - /sap/opu/odata/sap/API_SALES_ORDER_SRV         销售订单
  - /sap/opu/odata/sap/API_PRODUCT_SRV              物料主数据
  - /sap/opu/odata/sap/API_BILL_OF_MATERIAL_SRV_0002  BOM
  - /sap/opu/odata/sap/API_STOCK_ON_HAND_SRV       实时库存

认证：Basic Auth 或 OAuth2（通过 connector 的 username/password 或 api_key）。
"""
import base64
import logging
from typing import Any

from app.integration.adapters.base import (
    RemoteBom,
    RemoteBomItem,
    RemoteInventory,
    RemoteMaterial,
    RemoteOrder,
    RemoteOrderItem,
)
from app.integration.adapters.http_base import BaseHttpAdapter
from app.integration.config import SystemConnector

logger = logging.getLogger("delv-sog.integration.sap")


def _odata_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "d" in payload:
            d = payload["d"]
            if isinstance(d, list):
                return d
            if isinstance(d, dict):
                return d.get("results", [])
        if "value" in payload and isinstance(payload["value"], list):
            return payload["value"]
    return []


class SapS4Adapter(BaseHttpAdapter):
    system_name = "SAP"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)

    @property
    def _http_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.connector.username and self.connector.password:
            token = base64.b64encode(
                f"{self.connector.username}:{self.connector.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {token}"
        elif self.connector.api_key:
            headers["Authorization"] = f"Bearer {self.connector.api_key}"
        return headers

    async def test_connection(self) -> dict[str, Any]:
        try:
            data = await self._get(
                "/sap/opu/odata/sap/API_PRODUCT_SRV/$metadata"
            )
            return {"ok": True, "detail": "SAP OData service reachable"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def fetch_orders(self, since: str | None = None) -> list[RemoteOrder]:
        params = {}
        if since:
            params["$filter"] = f"SalesOrderDate ge datetime'{since}'"
        params["$expand"] = "to_Item"
        params["$top"] = "500"

        data = await self._get(
            "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder",
            params=params,
        )
        results = []
        for row in _odata_items(data):
            items = []
            for it in row.get("to_Item", {}).get("results", []):
                items.append(RemoteOrderItem(
                    external_id=str(it.get("SalesOrderItem", "")),
                    line_no=int(it.get("SalesOrderItem", 1)),
                    material_code=it.get("Material", ""),
                    material_name=it.get("MaterialName", ""),
                    qty=float(it.get("RequestedQuantity", 0)),
                    unit=it.get("RequestedQuantityUnit", "PCS"),
                ))
            results.append(RemoteOrder(
                external_id=str(row.get("SalesOrder", "")),
                order_no=row.get("SalesOrder", ""),
                customer_name=row.get("SoldToParty", ""),
                product_model=items[0].material_code if items else "",
                planned_date=str(row.get("SalesOrderDate", ""))[:10],
                items=items,
            ))
        return results

    async def fetch_materials(self, since: str | None = None) -> list[RemoteMaterial]:
        params = {"$top": "2000", "$select": "Product,ProductType,ProductDescription"}
        if since:
            params["$filter"] = f"LastChangeDateTime ge datetime'{since}'"
        data = await self._get(
            "/sap/opu/odata/sap/API_PRODUCT_SRV/A_Product",
            params=params,
        )
        results = []
        for row in _odata_items(data):
            product_type = row.get("ProductType", "FERT")
            type_map = {"RAW": "RAW", "HALB": "SEMI", "FERT": "FINISHED", "DIEN": "WIP"}
            results.append(RemoteMaterial(
                external_id=str(row.get("Product", "")),
                code=row.get("Product", ""),
                name=row.get("ProductDescription", ""),
                type=type_map.get(product_type, "RAW"),
            ))
        return results

    async def fetch_boms(self, since: str | None = None) -> list[RemoteBom]:
        params = {"$expand": "to_BomItem", "$top": "500"}
        data = await self._get(
            "/sap/opu/odata/sap/API_BILL_OF_MATERIAL_SRV_0002/A_BillOfMaterial",
            params=params,
        )
        results = []
        for row in _odata_items(data):
            items = []
            for it in row.get("to_BomItem", {}).get("results", []):
                items.append(RemoteBomItem(
                    component_code=it.get("ComponentMaterial", ""),
                    component_name=it.get("MaterialName", ""),
                    qty=float(it.get("ComponentQuantity", 1)),
                    loss_rate=float(it.get("ComponentScrapInPercent", 0)) / 100,
                    seq=int(it.get("BomItemNodeNumber", 1)),
                ))
            results.append(RemoteBom(
                external_id=str(row.get("BillOfMaterialInternalID", row.get("Material", ""))),
                product_code=row.get("Material", ""),
                version=row.get("BillOfMaterialVariant", "1"),
                is_active=row.get("BillOfMaterialIsActive", "X") == "X",
                items=items,
            ))
        return results

    async def fetch_inventory(self, since: str | None = None) -> list[RemoteInventory]:
        params = {"$top": "1000"}
        data = await self._get(
            "/sap/opu/odata/sap/API_STOCK_ON_HAND_SRV/A_StockOnHand",
            params=params,
        )
        results = []
        for row in _odata_items(data):
            results.append(RemoteInventory(
                external_id=str(row.get("StockIdentifier", "")),
                material_code=row.get("Material", ""),
                batch_no=row.get("Batch", ""),
                location=row.get("StorageLocation", ""),
                qty_on_hand=float(row.get("UnrestrictedUseStock", 0)),
                qty_reserved=float(row.get("RestrictedStock", 0)),
            ))
        return results
"""金蝶云星空 REST API 适配器。

金蝶云星空（Kingdee Cloud Cosmic）和金蝶云苍穹 提供统一 REST OpenAPI：
  - POST /k3cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Execute.common.kdsvc
  - GET  /k3cloud/Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc

认证流程：
  1. ValidateUser: username + password → get cookie `kdservice-sessionid`
  2. 后续请求自动携带 cookie，或使用 access_token + x-acgw-identity 头

常用业务表单 FormId：
  - SAL_ORDER     销售订单
  - BD_MATERIAL   物料
  - PBOM          客户BOM (或 BOM)
  - STK_INVENTORY 实时库存
"""
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

logger = logging.getLogger("delv-sog.integration.kingdee")


def _kd_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        result = payload.get("Result", payload)
        if isinstance(result, dict):
            rows = result.get("Rows", result.get("Data", []))
            return rows if isinstance(rows, list) else []
    return []


class KingdeeAdapter(BaseHttpAdapter):
    system_name = "KINGDEE"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)
        self._session_cookie: str | None = None

    @property
    def _http_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._session_cookie:
            headers["Cookie"] = f"kdservice-sessionid={self._session_cookie}"
        if self.connector.api_key:
            headers["access_token"] = self.connector.api_key
        identity = self.connector.extra.get("x_acgw_identity")
        if identity:
            headers["x-acgw-identity"] = identity
        return headers

    async def _ensure_auth(self):
        if self._session_cookie or self.connector.api_key:
            return
        username = self.connector.extra.get("username") or self.connector.username
        password = self.connector.extra.get("password") or self.connector.password
        if not username or not password:
            return
        import httpx
        url = self.connector.base_url.rstrip("/") + "/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc"
        async with httpx.AsyncClient(timeout=self.connector.timeout_seconds) as client:
            resp = await client.post(url, json={"acctID": self.connector.extra.get("acct_id", ""), "username": username, "password": password})
            resp.raise_for_status()
            self._session_cookie = resp.cookies.get("kdservice-sessionid")

    async def test_connection(self) -> dict[str, Any]:
        try:
            await self._ensure_auth()
            data = await self._get(
                "/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.GetCommonInfo.common.kdsvc"
            )
            return {"ok": True, "detail": "金蝶云接口可达"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _query(self, form_id: str, field_keys: str, limit: int = 500) -> list[dict[str, Any]]:
        await self._ensure_auth()
        payload = {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": "",
            "Limit": limit,
        }
        data = await self._post(
            "/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.ExecuteBillQuery.common.kdsvc",
            data=payload,
        )
        return _kd_items(data)

    async def fetch_orders(self, since: str | None = None) -> list[RemoteOrder]:
        field_keys = "FBillNo,FDate,FSaleOrgId,FSaleDeptId,Customer.FName,FStatus"
        rows = await self._query("SAL_ORDER", field_keys)
        results = []
        for row in rows:
            items_raw = row.get("SAL_ORDEREntry", row.get("Entry", []))
            items = []
            if isinstance(items_raw, list):
                for it in items_raw:
                    items.append(RemoteOrderItem(
                        external_id=str(it.get("EntryId", it.get("FRowId", ""))),
                        line_no=int(it.get("FEntryID", it.get("FRows", 1)) or 1),
                        material_code=it.get("Material.FNumber", ""),
                        material_name=it.get("Material.FName", ""),
                        qty=float(it.get("FQty", 0)),
                        unit=it.get("FUnit.FName", "PCS"),
                    ))
            customer = row.get("Customer.FName", row.get("CSaleCustomer", ""))
            results.append(RemoteOrder(
                external_id=str(row.get("FBillNo", "")),
                order_no=row.get("FBillNo", ""),
                customer_name=customer,
                product_model=items[0].material_code if items else "",
                planned_date=str(row.get("FDate", ""))[:10],
                items=items,
            ))
        return results

    async def fetch_materials(self, since: str | None = None) -> list[RemoteMaterial]:
        field_keys = "FNumber,FName,FSpecification,FUnit.FNumber,FMaterialType"
        rows = await self._query("BD_MATERIAL", field_keys, limit=2000)
        type_map = {"1": "RAW", "2": "FINISHED", "3": "SEMI", "4": "WIP"}
        results = []
        for row in rows:
            results.append(RemoteMaterial(
                external_id=str(row.get("FNumber", "")),
                code=row.get("FNumber", ""),
                name=row.get("FName", ""),
                type=type_map.get(str(row.get("FMaterialType", "")), "RAW"),
                spec=row.get("FSpecification", ""),
                unit=row.get("FUnit.FNumber", "PCS"),
            ))
        return results

    async def fetch_boms(self, since: str | None = None) -> list[RemoteBom]:
        field_keys = "FBomNo,FMaterialId,FVersion,FIsActive"
        rows = await self._query("PBOM", field_keys, limit=500)
        results = []
        for row in rows:
            items_raw = row.get("PBOMEntry", row.get("Entry", []))
            items = []
            if isinstance(items_raw, list):
                for it in items_raw:
                    items.append(RemoteBomItem(
                        component_code=it.get("Material.FNumber", ""),
                        component_name=it.get("Material.FName", ""),
                        qty=float(it.get("FQty", 1)),
                        loss_rate=float(it.get("FLossRate", 0)) / 100,
                        seq=int(it.get("FSeq", 1)),
                    ))
            product_code = row.get("FMaterialId.FNumber", "") if isinstance(row.get("FMaterialId"), dict) else str(row.get("FMaterialId", ""))
            results.append(RemoteBom(
                external_id=str(row.get("FBomNo", "")),
                product_code=product_code,
                version=str(row.get("FVersion", "V1")),
                is_active=row.get("FIsActive", "1") in ("1", True, "True"),
                items=items,
            ))
        return results

    async def fetch_inventory(self, since: str | None = None) -> list[RemoteInventory]:
        field_keys = "FMaterial.FNumber,FBatchNo,FStock.FNumber,FQty,FStockQty,FLockQty"
        rows = await self._query("STK_INVENTORY", field_keys, limit=2000)
        results = []
        for row in rows:
            material_code = row.get("FMaterial.FNumber", "") if isinstance(row.get("FMaterial"), dict) else str(row.get("FMaterial", ""))
            location = row.get("FStock.FNumber", "") if isinstance(row.get("FStock"), dict) else str(row.get("FStock", ""))
            results.append(RemoteInventory(
                external_id=str(row.get("FID", "")),
                material_code=material_code,
                batch_no=row.get("FBatchNo", ""),
                location=location,
                qty_on_hand=float(row.get("FQty", row.get("FStockQty", 0))),
                qty_reserved=float(row.get("FLockQty", 0)),
            ))
        return results
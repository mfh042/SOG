"""用友 NC Cloud / YonBIP OpenAPI 适配器。

用友开放平台提供 RESTful API，采用 AK/SK 签名认证：
  - 请求头包含 appkey + signature + tenantId + timestamp
  - 签名算法：HMAC-SHA256(secret,  canonical_string)

常用端点：
  - /api/apppub/salesorder/query          销售订单
  - /api/apppub/material/query            物料主数据
  - /api/apppub/bom/query                 BOM
  - /api/apppub/inventory/query           实时库存

也兼容 用友 U8+/U9 的简单 appkey+token 认证模式。
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

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

logger = logging.getLogger("delv-sog.integration.yonyou")


def _yy_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "items", "list", "data", "result"):
            if key in payload:
                val = payload[key]
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    for k2 in ("rows", "items", "list"):
                        if k2 in val and isinstance(val[k2], list):
                            return val[k2]
    return []


class YonyouAdapter(BaseHttpAdapter):
    system_name = "YONYOU"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)

    @property
    def _app_key(self) -> str:
        return self.connector.extra.get("app_key") or self.connector.extra.get("ak") or self.connector.username or ""

    @property
    def _app_secret(self) -> str:
        return self.connector.extra.get("app_secret") or self.connector.extra.get("sk") or self.connector.password or ""

    @property
    def _tenant_id(self) -> str:
        return self.connector.extra.get("tenant_id") or self.connector.extra.get("tenantId") or ""

    def _sign(self, method: str, path: str, timestamp: str, body_str: str = "") -> str:
        canonical = f"{method.upper()}\n{path}\n{timestamp}\n{body_str}"
        secret = self._app_secret.encode("utf-8")
        message = canonical.encode("utf-8")
        sig = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return sig

    @property
    def _http_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.connector.api_key and not self._app_key:
            headers["Authorization"] = f"Bearer {self.connector.api_key}"
            if self._tenant_id:
                headers["tenantId"] = self._tenant_id
            return headers

        timestamp = str(int(time.time() * 1000))
        signature = self._sign("GET", "", timestamp, "")
        headers.update({
            "appkey": self._app_key,
            "signature": signature,
            "timestamp": timestamp,
        })
        if self._tenant_id:
            headers["tenantId"] = self._tenant_id
        return headers

    async def _yy_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self.connector.base_url.rstrip("/") + path
        headers = dict(self._http_headers)
        timeout = httpx.Timeout(self.connector.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def _yy_post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        url = self.connector.base_url.rstrip("/") + path
        body_str = json.dumps(data or {}, ensure_ascii=False, sort_keys=True)
        timestamp = str(int(time.time() * 1000))
        signature = self._sign("POST", path, timestamp, body_str)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "appkey": self._app_key,
            "signature": signature,
            "timestamp": timestamp,
        }
        if self._tenant_id:
            headers["tenantId"] = self._tenant_id
        timeout = httpx.Timeout(self.connector.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, content=body_str)
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> dict[str, Any]:
        try:
            data = await self._yy_get("/api/apppub/ping")
            return {"ok": True, "detail": str(data)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def fetch_orders(self, since: str | None = None) -> list[RemoteOrder]:
        params = {"pageSize": 500}
        if since:
            params["modifiedSince"] = since
        data = await self._yy_get("/api/apppub/salesorder/query", params=params)
        rows = _yy_items(data)
        results = []
        for row in rows:
            items_raw = row.get("items", row.get("entrys", row.get("body", [])))
            items = []
            if isinstance(items_raw, list):
                for it in items_raw:
                    items.append(RemoteOrderItem(
                        external_id=str(it.get("id", it.get("rowId", ""))),
                        line_no=int(it.get("rowNo", it.get("entryId", 1)) or 1),
                        material_code=it.get("materialCode", it.get("productCode", "")),
                        material_name=it.get("materialName", it.get("productName", "")),
                        qty=float(it.get("quantity", it.get("qty", 0))),
                        unit=it.get("unit", "PCS"),
                    ))
            results.append(RemoteOrder(
                external_id=str(row.get("id", row.get("orderId", row.get("code", "")))),
                order_no=row.get("code", row.get("orderNo", "")),
                customer_name=row.get("customerName", row.get("customer", "")),
                product_model=items[0].material_code if items else "",
                planned_date=str(row.get("planDate", row.get("deliveryDate", "")))[:10],
                items=items,
            ))
        return results

    async def fetch_materials(self, since: str | None = None) -> list[RemoteMaterial]:
        params = {"pageSize": 2000}
        if since:
            params["modifiedSince"] = since
        data = await self._yy_get("/api/apppub/material/query", params=params)
        rows = _yy_items(data)
        type_map = {"1": "RAW", "2": "FINISHED", "3": "SEMI", "4": "WIP", "RAW": "RAW", "FINISHED": "FINISHED", "SEMI": "SEMI"}
        results = []
        for row in rows:
            results.append(RemoteMaterial(
                external_id=str(row.get("id", row.get("materialId", ""))),
                code=row.get("code", row.get("materialCode", row.get("number", ""))),
                name=row.get("name", row.get("materialName", row.get("description", ""))),
                type=type_map.get(str(row.get("type", row.get("materialType", ""))), "RAW"),
                spec=row.get("spec", row.get("specModel", "")),
                unit=row.get("unit", row.get("baseUnit", "PCS")),
            ))
        return results

    async def fetch_boms(self, since: str | None = None) -> list[RemoteBom]:
        params = {"pageSize": 500}
        data = await self._yy_get("/api/apppub/bom/query", params=params)
        rows = _yy_items(data)
        results = []
        for row in rows:
            items_raw = row.get("items", row.get("entrys", row.get("bomItems", [])))
            items = []
            if isinstance(items_raw, list):
                for it in items_raw:
                    items.append(RemoteBomItem(
                        component_code=it.get("componentCode", it.get("materialCode", "")),
                        component_name=it.get("componentName", it.get("materialName", "")),
                        qty=float(it.get("quantity", it.get("qty", 1))),
                        loss_rate=float(it.get("lossRate", it.get("scrapRate", 0))),
                        seq=int(it.get("seq", it.get("rowNo", 1))),
                    ))
            results.append(RemoteBom(
                external_id=str(row.get("id", row.get("bomId", ""))),
                product_code=row.get("productCode", row.get("materialCode", "")),
                version=str(row.get("version", row.get("bomVersion", "V1"))),
                is_active=row.get("isActive", row.get("active", True)),
                items=items,
            ))
        return results

    async def fetch_inventory(self, since: str | None = None) -> list[RemoteInventory]:
        params = {"pageSize": 2000}
        data = await self._yy_get("/api/apppub/inventory/query", params=params)
        rows = _yy_items(data)
        results = []
        for row in rows:
            results.append(RemoteInventory(
                external_id=str(row.get("id", row.get("invId", ""))),
                material_code=row.get("materialCode", row.get("code", "")),
                batch_no=row.get("batchNo", row.get("lotNo", "")),
                location=row.get("warehouseCode", row.get("whCode", row.get("location", ""))),
                qty_on_hand=float(row.get("onHand", row.get("quantity", row.get("qty", 0)))),
                qty_reserved=float(row.get("reserved", row.get("lockQty", 0))),
            ))
        return results
from typing import Any

from fastapi import APIRouter, Body, Query

from app.core.response import Resp
from app.integration.adapters.registry import registry
from app.integration.config_store import (
    DATA_TYPE_KEYS,
    SYSTEM_FIELDS,
    SYSTEM_META,
    YONYOU_EXTRA_FIELDS,
    KINGDEE_EXTRA_FIELDS,
    delete_key,
    get_data_source_view,
    get_full_view,
    load_all_from_db,
    save_many,
    save_key,
    set_data_source,
)
from app.integration.enums import DataType
from app.integration.service import integration_service

router = APIRouter(prefix="/api/integration", tags=["系统集成"])


@router.get("/health", summary="集成健康检查")
async def integration_health():
    data = await integration_service.health()
    return Resp.ok(data)


@router.get("/systems", summary="列出已启用的外部系统")
async def list_systems():
    systems = integration_service.enabled_systems()
    return Resp.ok({
        "enabled": systems,
        "available_adapters": registry.available(),
    })


@router.get("/config", summary="获取完整集成配置")
async def get_config():
    merged = await get_full_view()
    db_only = await load_all_from_db()
    data_sources = await get_data_source_view()

    systems_out = []
    for meta in SYSTEM_META:
        prefix = meta["key"]
        fields = []
        for fdef in SYSTEM_FIELDS:
            key = fdef["key"].replace("{prefix}", prefix)
            val = merged.get(key, False if key.endswith("_ENABLED") else "")
            fields.append({
                "key": key,
                "label": fdef["label"],
                "type": fdef.get("type", "text"),
                "value": val,
                "from_db": key in db_only,
                "placeholder": fdef.get("placeholder", ""),
                "min": fdef.get("min"),
            })
        if prefix == "KINGDEE":
            for fdef in KINGDEE_EXTRA_FIELDS:
                fields.append({
                    "key": fdef["key"],
                    "label": fdef["label"],
                    "type": fdef.get("type", "text"),
                    "value": merged.get(fdef["key"], ""),
                    "from_db": fdef["key"] in db_only,
                })
        if prefix == "YONYOU":
            for fdef in YONYOU_EXTRA_FIELDS:
                fields.append({
                    "key": fdef["key"],
                    "label": fdef["label"],
                    "type": fdef.get("type", "text"),
                    "value": merged.get(fdef["key"], ""),
                    "from_db": fdef["key"] in db_only,
                })
        systems_out.append({
            "key": prefix,
            "label": meta["label"],
            "fields": fields,
            "enabled": bool(merged.get(f"{prefix}_ENABLED", False)),
        })

    sources_out = []
    for dt in DATA_TYPE_KEYS:
        sources_out.append({
            "data_type": dt,
            "label": {
                "ORDERS": "订单",
                "MATERIALS": "物料主数据",
                "BOM": "BOM 清单",
                "INVENTORY": "实时库存",
            }.get(dt, dt),
            "source": data_sources.get(dt, "LOCAL"),
        })

    return Resp.ok({
        "integration_mode": merged.get("INTEGRATION_MODE", "LOCAL"),
        "systems": systems_out,
        "data_sources": sources_out,
        "available_sources": registry.available(),
    })


@router.post("/config", summary="批量保存集成配置")
async def save_config(payload: list[dict[str, Any]] = Body(...)):
    await save_many(payload)
    integration_service.reload()
    return Resp.ok({"saved": len(payload)})


@router.post("/config/{key}/reset", summary="将某个配置项重置为 .env 默认值")
async def reset_config(key: str):
    await delete_key(key)
    integration_service.reload()
    return Resp.ok({"key": key, "reset": True})


@router.post("/data-source", summary="设置某数据类型的来源")
async def set_source(data_type: str = Body(..., embed=True), source: str = Body(..., embed=True)):
    await set_data_source(data_type, source)
    return Resp.ok({"data_type": data_type, "source": source})


@router.post("/sync/{system}/{data_type}", summary="手动触发单项同步")
async def sync_one(
    system: str,
    data_type: DataType,
):
    result = await integration_service.sync_one(system, data_type)
    return Resp.ok(result)


@router.post("/sync/{system}", summary="手动触发某系统全量同步")
async def sync_system(system: str):
    result = await integration_service.sync_all(system)
    return Resp.ok(result)


@router.post("/sync", summary="手动触发所有启用系统的全量同步")
async def sync_all_enabled():
    result = await integration_service.sync_all_enabled()
    return Resp.ok(result)


@router.get("/jobs", summary="同步任务历史")
async def list_sync_jobs(
    system: str | None = Query(default=None, description="过滤系统 ERP/MES/PLM/WMS"),
    data_type: str | None = Query(default=None, description="过滤数据类型 ORDERS/MATERIALS/BOM/INVENTORY"),
    limit: int = Query(default=50, ge=1, le=500),
):
    jobs = await integration_service.list_sync_jobs(system, data_type, limit)
    return Resp.ok(jobs)
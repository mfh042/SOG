"""集成配置存储层。

提供从数据库 `integration_config` 表读写 key-value 的能力，
以及将 DB 配置与 .env 默认值合并后的完整视图。
"""
import asyncio
import json
import logging
from typing import Any

from sqlalchemy import select, delete

from app.core.db import AsyncSessionLocal
from app.integration.config import integration_settings
from app.integration.models import IntegrationConfig

logger = logging.getLogger("delv-sog.integration.config-store")

SYS_KEYS = {
    "INTEGRATION_MODE",
    "SAP_ENABLED", "SAP_BASE_URL", "SAP_USERNAME", "SAP_PASSWORD", "SAP_API_KEY", "SAP_SYNC_INTERVAL",
    "KINGDEE_ENABLED", "KINGDEE_BASE_URL", "KINGDEE_API_KEY", "KINGDEE_USERNAME", "KINGDEE_PASSWORD",
    "KINGDEE_ACCT_ID", "KINGDEE_X_ACGW_IDENTITY", "KINGDEE_SYNC_INTERVAL",
    "YONYOU_ENABLED", "YONYOU_BASE_URL", "YONYOU_APP_KEY", "YONYOU_APP_SECRET",
    "YONYOU_TENANT_ID", "YONYOU_API_KEY", "YONYOU_SYNC_INTERVAL",
    "ERP_ENABLED", "ERP_BASE_URL", "ERP_API_KEY", "ERP_SYNC_INTERVAL",
    "MES_ENABLED", "MES_BASE_URL", "MES_API_KEY", "MES_SYNC_INTERVAL",
    "PLM_ENABLED", "PLM_BASE_URL", "PLM_API_KEY", "PLM_SYNC_INTERVAL",
    "WMS_ENABLED", "WMS_BASE_URL", "WMS_API_KEY", "WMS_SYNC_INTERVAL",
}

DATA_TYPE_KEYS = {"ORDERS", "MATERIALS", "BOM", "INVENTORY"}


def _coerce(key: str, raw: str) -> Any:
    if raw == "":
        return ""
    if key.endswith("_ENABLED") or key == "INTEGRATION_MODE":
        if key == "INTEGRATION_MODE":
            return raw.upper()
        return raw.lower() in ("true", "1", "yes", "on")
    if key.endswith("_SYNC_INTERVAL"):
        try:
            return int(raw)
        except ValueError:
            return 60
    return raw


async def load_all_from_db() -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        rows = (await session.scalars(select(IntegrationConfig))).all()
    result: dict[str, Any] = {}
    for row in rows:
        result[row.config_key] = _coerce(row.config_key, row.config_value)
    return result


async def save_key(key: str, value: Any, description: str = "") -> None:
    value_type = "string"
    if isinstance(value, bool):
        stored = "true" if value else "false"
        value_type = "bool"
    elif isinstance(value, int):
        stored = str(value)
        value_type = "int"
    else:
        stored = str(value)
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(IntegrationConfig).where(IntegrationConfig.config_key == key))
        if existing:
            existing.config_value = stored
            existing.value_type = value_type
            existing.description = description
        else:
            session.add(IntegrationConfig(config_key=key, config_value=stored, value_type=value_type, description=description))
        await session.commit()


async def save_many(items: list[dict[str, Any]]) -> None:
    async with AsyncSessionLocal() as session:
        for it in items:
            key = it["key"]
            value = it["value"]
            desc = it.get("description", "")
            value_type = "string"
            if isinstance(value, bool):
                stored = "true" if value else "false"
                value_type = "bool"
            elif isinstance(value, int):
                stored = str(value)
                value_type = "int"
            else:
                stored = str(value)
            existing = await session.scalar(select(IntegrationConfig).where(IntegrationConfig.config_key == key))
            if existing:
                existing.config_value = stored
                existing.value_type = value_type
                existing.description = desc
            else:
                session.add(IntegrationConfig(config_key=key, config_value=stored, value_type=value_type, description=desc))
        await session.commit()


async def delete_key(key: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(IntegrationConfig).where(IntegrationConfig.config_key == key))
        await session.commit()


def _read_attr(key: str) -> Any:
    return getattr(integration_settings, key.lower(), None)


async def get_full_view() -> dict[str, Any]:
    """合并 .env 默认值 + DB 覆盖值，返回完整配置视图。"""
    env_values = {k: _read_attr(k) for k in SYS_KEYS}
    db_values = await load_all_from_db()
    merged = {**env_values, **db_values}
    return merged


SYSTEM_META = [
    {"key": "SAP", "label": "SAP S/4HANA", "systems": ["sap"]},
    {"key": "KINGDEE", "label": "金蝶云星空 / 苍穹", "systems": ["kingdee"]},
    {"key": "YONYOU", "label": "用友 NC Cloud / YonBIP", "systems": ["yonyou"]},
    {"key": "ERP", "label": "通用 ERP", "systems": ["erp"]},
    {"key": "MES", "label": "通用 MES", "systems": ["mes"]},
    {"key": "PLM", "label": "通用 PLM", "systems": ["plm"]},
    {"key": "WMS", "label": "通用 WMS", "systems": ["wms"]},
]

SYSTEM_FIELDS = [
    {"key": "{prefix}_ENABLED", "label": "启用", "type": "switch", "description": "开启此外部系统的集成"},
    {"key": "{prefix}_BASE_URL", "label": "接口地址", "type": "text", "placeholder": "https://host:port"},
    {"key": "{prefix}_API_KEY", "label": "API Key / Token", "type": "password"},
    {"key": "{prefix}_USERNAME", "label": "用户名", "type": "text"},
    {"key": "{prefix}_PASSWORD", "label": "密码", "type": "password"},
    {"key": "{prefix}_SYNC_INTERVAL", "label": "同步间隔(分钟)", "type": "number", "min": 5},
]

KINGDEE_EXTRA_FIELDS = [
    {"key": "KINGDEE_ACCT_ID", "label": "金蝶账套 ID", "type": "text"},
    {"key": "KINGDEE_X_ACGW_IDENTITY", "label": "x-acgw-identity", "type": "text"},
]

YONYOU_EXTRA_FIELDS = [
    {"key": "YONYOU_APP_KEY", "label": "App Key (AK)", "type": "text"},
    {"key": "YONYOU_APP_SECRET", "label": "App Secret (SK)", "type": "password"},
    {"key": "YONYOU_TENANT_ID", "label": "租户 ID", "type": "text"},
]


async def get_data_source_view() -> dict[str, str]:
    """获取各数据类型的来源配置。"""
    db = await load_all_from_db()
    sources: dict[str, str] = {}
    for dt in DATA_TYPE_KEYS:
        key = f"DATA_SOURCE_{dt}"
        sources[dt] = db.get(key, "LOCAL")
    return sources


async def set_data_source(data_type: str, source: str) -> None:
    if data_type not in DATA_TYPE_KEYS:
        raise ValueError(f"Invalid data_type: {data_type}")
    source_upper = source.upper()
    key = f"DATA_SOURCE_{data_type}"
    await save_key(key, source_upper, description=f"{data_type} 数据来源：LOCAL 或 外部系统名")
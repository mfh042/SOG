import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.integration.adapters.base import ExternalSystemAdapter
from app.integration.adapters.local import LocalModeAdapter
from app.integration.adapters.registry import registry
from app.integration.config import SystemConnector, integration_settings
from app.integration.config_store import load_all_from_db
from app.integration.enums import DataType, ExternalSystem, SyncStatus
from app.integration.models import SyncJob
from app.integration.sync.boms import sync_boms
from app.integration.sync.inventory import sync_inventory
from app.integration.sync.materials import sync_materials
from app.integration.sync.orders import sync_orders

logger = logging.getLogger("delv-sog.integration")

_SYSTEM_NAMES = ["erp", "mes", "plm", "wms", "sap", "kingdee", "yonyou"]
_NAME_MAP = {n.upper(): n for n in _SYSTEM_NAMES}


async def _build_connector(system_key: str, db_vals: dict[str, Any] | None = None) -> SystemConnector:
    """构建某个系统的 connector，db_vals 会覆盖 .env 默认值。"""
    key = _NAME_MAP.get(system_key.upper(), system_key.lower())
    getter = getattr(integration_settings, key, None)
    base = getter if isinstance(getter, SystemConnector) else SystemConnector()

    db_vals = db_vals or {}
    prefix = key.upper()
    enabled = db_vals.get(f"{prefix}_ENABLED", base.enabled)
    base_url = db_vals.get(f"{prefix}_BASE_URL", base.base_url)
    api_key = db_vals.get(f"{prefix}_API_KEY", base.api_key)
    username = db_vals.get(f"{prefix}_USERNAME", base.username)
    password = db_vals.get(f"{prefix}_PASSWORD", base.password)
    interval = db_vals.get(f"{prefix}_SYNC_INTERVAL", base.sync_interval_minutes)

    extra = dict(base.extra)
    if prefix == "KINGDEE":
        extra["acct_id"] = db_vals.get("KINGDEE_ACCT_ID", base.extra.get("acct_id", ""))
        extra["x_acgw_identity"] = db_vals.get("KINGDEE_X_ACGW_IDENTITY", base.extra.get("x_acgw_identity", ""))
    if prefix == "YONYOU":
        extra["app_key"] = db_vals.get("YONYOU_APP_KEY", base.extra.get("app_key", ""))
        extra["app_secret"] = db_vals.get("YONYOU_APP_SECRET", base.extra.get("app_secret", ""))
        extra["tenant_id"] = db_vals.get("YONYOU_TENANT_ID", base.extra.get("tenant_id", ""))

    return SystemConnector(
        enabled=bool(enabled),
        base_url=str(base_url or ""),
        api_key=str(api_key or ""),
        username=str(username or ""),
        password=str(password or ""),
        sync_interval_minutes=int(interval or 60),
        extra=extra,
    )


def _build_job(
    system: str, data_type: str, trigger_type: str = "MANUAL"
) -> SyncJob:
    return SyncJob(
        system=system.upper(),
        data_type=data_type.upper(),
        trigger_type=trigger_type,
        status=SyncStatus.RUNNING.value,
    )


async def _run_sync(
    session: AsyncSession,
    adapter: ExternalSystemAdapter,
    data_type: DataType,
    system: str,
) -> dict[str, Any]:
    job = _build_job(system, data_type.value)
    session.add(job)
    await session.flush()

    try:
        if data_type == DataType.ORDERS:
            remote_data = await adapter.fetch_orders()
            await sync_orders(session, system.upper(), remote_data, job)
        elif data_type == DataType.MATERIALS:
            remote_data = await adapter.fetch_materials()
            await sync_materials(session, system.upper(), remote_data, job)
        elif data_type == DataType.BOM:
            remote_data = await adapter.fetch_boms()
            await sync_boms(session, system.upper(), remote_data, job)
        elif data_type == DataType.INVENTORY:
            remote_data = await adapter.fetch_inventory()
            await sync_inventory(session, system.upper(), remote_data, job)
        else:
            job.status = SyncStatus.FAILED.value
            job.error_message = f"Unsupported data type: {data_type}"
            job.finished_at = datetime.utcnow()
            await session.commit()
            return {"status": "FAILED", "error": job.error_message}

        job.status = SyncStatus.SUCCESS.value
        if job.records_failed > 0:
            job.status = SyncStatus.PARTIAL.value
        job.finished_at = datetime.utcnow()
        await session.commit()

        return {
            "status": job.status,
            "records_fetched": job.records_fetched,
            "records_created": job.records_created,
            "records_updated": job.records_updated,
            "records_failed": job.records_failed,
        }
    except Exception as e:
        logger.exception("Sync failed for %s/%s", system, data_type)
        job.status = SyncStatus.FAILED.value
        job.finished_at = datetime.utcnow()
        job.error_message = str(e)
        await session.commit()
        return {"status": "FAILED", "error": str(e)}


class IntegrationService:
    def __init__(self):
        self._ensure_registry()
        self._db_cache: dict[str, Any] | None = None

    def reload(self):
        self._db_cache = None
        registry.clear()
        self._ensure_registry()
        logger.info("Integration service reloaded")

    def _ensure_registry(self):
        from app.integration.adapters.erp import GenericErpAdapter
        from app.integration.adapters.local import LocalModeAdapter
        from app.integration.adapters.mes import GenericMesAdapter
        from app.integration.adapters.plm import GenericPlmAdapter
        from app.integration.adapters.wms import GenericWmsAdapter
        from app.integration.adapters.vendors.sap import SapS4Adapter
        from app.integration.adapters.vendors.kingdee import KingdeeAdapter
        from app.integration.adapters.vendors.yonyou import YonyouAdapter

        if ExternalSystem.LOCAL.value not in registry._adapters:
            registry.register(LocalModeAdapter)
        if ExternalSystem.ERP.value not in registry._adapters:
            registry.register(GenericErpAdapter)
        if ExternalSystem.MES.value not in registry._adapters:
            registry.register(GenericMesAdapter)
        if ExternalSystem.PLM.value not in registry._adapters:
            registry.register(GenericPlmAdapter)
        if ExternalSystem.WMS.value not in registry._adapters:
            registry.register(GenericWmsAdapter)
        if "SAP" not in registry._adapters:
            registry.register(SapS4Adapter)
        if "KINGDEE" not in registry._adapters:
            registry.register(KingdeeAdapter)
        if "YONYOU" not in registry._adapters:
            registry.register(YonyouAdapter)

    async def _db_values(self) -> dict[str, Any]:
        if self._db_cache is None:
            self._db_cache = await load_all_from_db()
        return self._db_cache

    async def _connector_for(self, system_key: str) -> SystemConnector:
        db_vals = await self._db_values()
        return await _build_connector(system_key, db_vals)

    async def _local_mode(self) -> bool:
        db_vals = await self._db_values()
        mode = db_vals.get("INTEGRATION_MODE")
        if mode:
            return str(mode).upper() == "LOCAL"
        mode_attr = getattr(integration_settings, "integration_mode", "LOCAL")
        if str(mode_attr).upper() == "LOCAL":
            return True
        connectors = [await self._connector_for(n) for n in _SYSTEM_NAMES]
        return not any(c.enabled for c in connectors)

    async def get_adapter(self, system: str) -> ExternalSystemAdapter | None:
        system_upper = system.upper()
        if system_upper == ExternalSystem.LOCAL.value or await self._local_mode():
            return registry.get(ExternalSystem.LOCAL.value)

        connector = await self._connector_for(system_upper)
        if connector.enabled:
            return registry.get(system_upper, connector)
        return None

    async def enabled_systems(self) -> list[str]:
        if await self._local_mode():
            return [ExternalSystem.LOCAL.value]
        out = []
        for name in _SYSTEM_NAMES:
            connector = await self._connector_for(name)
            if connector.enabled:
                out.append(name.upper())
        return out

    async def health(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mode": "LOCAL" if await self._local_mode() else "INTEGRATED",
            "systems": {},
        }
        for sys_name in await self.enabled_systems():
            adapter = await self.get_adapter(sys_name)
            if adapter:
                result["systems"][sys_name] = await adapter.test_connection()
        return result

    async def sync_one(self, system: str, data_type: DataType) -> dict[str, Any]:
        adapter = await self.get_adapter(system)
        if not adapter:
            return {"status": "SKIPPED", "reason": f"Adapter for {system} not available"}
        async with AsyncSessionLocal() as session:
            return await _run_sync(session, adapter, data_type, system)

    async def sync_all(self, system: str) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for dt in DataType:
            if dt == DataType.CUSTOMERS:
                continue
            results[dt.value] = await self.sync_one(system, dt)
        return results

    async def sync_all_enabled(self) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for sys_name in await self.enabled_systems():
            summary[sys_name] = await self.sync_all(sys_name)
        return summary

    async def list_sync_jobs(
        self,
        system: str | None = None,
        data_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(SyncJob)
            if system:
                stmt = stmt.where(SyncJob.system == system.upper())
            if data_type:
                stmt = stmt.where(SyncJob.data_type == data_type.upper())
            stmt = stmt.order_by(SyncJob.id.desc()).limit(limit)
            rows = list((await session.scalars(stmt)).all())
            return [
                {
                    "id": j.id,
                    "system": j.system,
                    "data_type": j.data_type,
                    "trigger_type": j.trigger_type,
                    "status": j.status,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                    "records_fetched": j.records_fetched,
                    "records_created": j.records_created,
                    "records_updated": j.records_updated,
                    "records_failed": j.records_failed,
                    "error_message": j.error_message,
                }
                for j in rows
            ]


integration_service = IntegrationService()
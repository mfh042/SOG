import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.adapters.base import RemoteInventory
from app.integration.models import ExternalIdMapping, SyncJob
from app.modules.material.models import Inventory, Material

logger = logging.getLogger("delv-sog.integration.sync")


async def sync_inventory(
    session: AsyncSession,
    system: str,
    inventory: list[RemoteInventory],
    job: SyncJob,
) -> SyncJob:
    job.records_fetched = len(inventory)
    created = updated = failed = 0

    for remote in inventory:
        try:
            material = await session.scalar(
                select(Material).where(Material.code == remote.material_code)
            )
            if not material:
                logger.warning("库存同步跳过：物料 %s 不存在", remote.material_code)
                failed += 1
                continue

            mapping_stmt = select(ExternalIdMapping).where(
                ExternalIdMapping.system == system,
                ExternalIdMapping.data_type == "INVENTORY",
                ExternalIdMapping.external_id == remote.external_id,
            )
            mapping = await session.scalar(mapping_stmt)

            if mapping:
                inv = await session.get(Inventory, mapping.local_id)
                if inv:
                    inv.qty_on_hand = remote.qty_on_hand
                    inv.qty_reserved = remote.qty_reserved
                    mapping.last_synced_at = datetime.utcnow()
                    updated += 1
                    continue

            inv = await session.scalar(
                select(Inventory).where(
                    Inventory.material_id == material.id,
                    Inventory.batch_no == remote.batch_no,
                    Inventory.location == remote.location,
                )
            )
            if inv:
                inv.qty_on_hand = remote.qty_on_hand
                inv.qty_reserved = remote.qty_reserved
                session.add(ExternalIdMapping(
                    system=system,
                    data_type="INVENTORY",
                    external_id=remote.external_id,
                    local_table="inventory",
                    local_id=inv.id,
                    external_code=f"{remote.material_code}-{remote.batch_no}-{remote.location}",
                    last_synced_at=datetime.utcnow(),
                ))
                updated += 1
            else:
                inv = Inventory(
                    material_id=material.id,
                    batch_no=remote.batch_no,
                    location=remote.location or "WH-01",
                    qty_on_hand=remote.qty_on_hand,
                    qty_reserved=remote.qty_reserved,
                )
                session.add(inv)
                await session.flush()
                session.add(ExternalIdMapping(
                    system=system,
                    data_type="INVENTORY",
                    external_id=remote.external_id,
                    local_table="inventory",
                    local_id=inv.id,
                    external_code=f"{remote.material_code}-{remote.batch_no}-{remote.location}",
                    last_synced_at=datetime.utcnow(),
                ))
                created += 1
        except Exception as e:
            failed += 1
            logger.exception("Failed to sync inventory for %s: %s", remote.material_code, e)

    job.records_created = created
    job.records_updated = updated
    job.records_failed = failed
    return job
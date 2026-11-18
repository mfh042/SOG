import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.adapters.base import RemoteBom
from app.integration.models import ExternalIdMapping, SyncJob
from app.modules.bom.models import Bom, BomItem
from app.modules.material.models import Material

logger = logging.getLogger("delv-sog.integration.sync")


async def sync_boms(
    session: AsyncSession,
    system: str,
    boms: list[RemoteBom],
    job: SyncJob,
) -> SyncJob:
    job.records_fetched = len(boms)
    created = updated = failed = 0

    for remote in boms:
        try:
            product = await session.scalar(
                select(Material).where(Material.code == remote.product_code)
            )
            if not product:
                logger.warning("BOM 同步跳过：产品物料 %s 不存在", remote.product_code)
                failed += 1
                continue

            mapping_stmt = select(ExternalIdMapping).where(
                ExternalIdMapping.system == system,
                ExternalIdMapping.data_type == "BOM",
                ExternalIdMapping.external_id == remote.external_id,
            )
            mapping = await session.scalar(mapping_stmt)

            bom = None
            if mapping:
                bom = await session.get(Bom, mapping.local_id)

            if not bom:
                existing = await session.scalar(
                    select(Bom).where(
                        Bom.product_material_id == product.id,
                        Bom.version == remote.version,
                    )
                )
                if existing:
                    bom = existing

            if bom:
                await session.delete(
                    select(BomItem).where(BomItem.bom_id == bom.id)
                )
                await session.flush()
                for idx, it in enumerate(remote.items, start=1):
                    comp = await session.scalar(
                        select(Material).where(Material.code == it.component_code)
                    )
                    if not comp:
                        logger.warning("BOM 组件 %s 未找到，跳过", it.component_code)
                        continue
                    session.add(BomItem(
                        bom_id=bom.id,
                        component_material_id=comp.id,
                        qty=it.qty,
                        loss_rate=it.loss_rate,
                        seq=it.seq or idx,
                    ))
                bom.is_active = remote.is_active
                if mapping:
                    mapping.last_synced_at = datetime.utcnow()
                else:
                    session.add(ExternalIdMapping(
                        system=system,
                        data_type="BOM",
                        external_id=remote.external_id,
                        local_table="bom",
                        local_id=bom.id,
                        external_code=remote.product_code,
                        last_synced_at=datetime.utcnow(),
                    ))
                updated += 1
            else:
                bom = Bom(
                    product_material_id=product.id,
                    version=remote.version,
                    is_active=remote.is_active,
                )
                session.add(bom)
                await session.flush()
                for idx, it in enumerate(remote.items, start=1):
                    comp = await session.scalar(
                        select(Material).where(Material.code == it.component_code)
                    )
                    if not comp:
                        logger.warning("BOM 组件 %s 未找到，跳过", it.component_code)
                        continue
                    session.add(BomItem(
                        bom_id=bom.id,
                        component_material_id=comp.id,
                        qty=it.qty,
                        loss_rate=it.loss_rate,
                        seq=it.seq or idx,
                    ))
                session.add(ExternalIdMapping(
                    system=system,
                    data_type="BOM",
                    external_id=remote.external_id,
                    local_table="bom",
                    local_id=bom.id,
                    external_code=remote.product_code,
                    last_synced_at=datetime.utcnow(),
                ))
                created += 1
        except Exception as e:
            failed += 1
            logger.exception("Failed to sync BOM for %s: %s", remote.product_code, e)

    job.records_created = created
    job.records_updated = updated
    job.records_failed = failed
    return job
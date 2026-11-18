import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.adapters.base import RemoteMaterial
from app.integration.models import ExternalIdMapping, SyncJob
from app.modules.material.models import Material

logger = logging.getLogger("delv-sog.integration.sync")


async def sync_materials(
    session: AsyncSession,
    system: str,
    materials: list[RemoteMaterial],
    job: SyncJob,
) -> SyncJob:
    job.records_fetched = len(materials)
    created = updated = failed = 0

    for remote in materials:
        try:
            mapping_stmt = select(ExternalIdMapping).where(
                ExternalIdMapping.system == system,
                ExternalIdMapping.data_type == "MATERIALS",
                ExternalIdMapping.external_id == remote.external_id,
            )
            mapping = await session.scalar(mapping_stmt)

            if mapping:
                mat = await session.get(Material, mapping.local_id)
                if mat:
                    mat.name = remote.name
                    mat.type = remote.type
                    mat.spec = remote.spec
                    mat.unit = remote.unit
                    mapping.last_synced_at = datetime.utcnow()
                    updated += 1
                else:
                    mat = Material(
                        code=remote.code,
                        name=remote.name,
                        type=remote.type,
                        spec=remote.spec,
                        unit=remote.unit,
                    )
                    session.add(mat)
                    await session.flush()
                    mapping.local_id = mat.id
                    mapping.last_synced_at = datetime.utcnow()
                    updated += 1
            else:
                mat = await session.scalar(
                    select(Material).where(Material.code == remote.code)
                )
                if mat:
                    mat.name = remote.name
                    mat.type = remote.type
                    mat.spec = remote.spec
                    mat.unit = remote.unit
                    session.add(ExternalIdMapping(
                        system=system,
                        data_type="MATERIALS",
                        external_id=remote.external_id,
                        local_table="material",
                        local_id=mat.id,
                        external_code=remote.code,
                        last_synced_at=datetime.utcnow(),
                    ))
                    updated += 1
                else:
                    mat = Material(
                        code=remote.code,
                        name=remote.name,
                        type=remote.type,
                        spec=remote.spec,
                        unit=remote.unit,
                    )
                    session.add(mat)
                    await session.flush()
                    session.add(ExternalIdMapping(
                        system=system,
                        data_type="MATERIALS",
                        external_id=remote.external_id,
                        local_table="material",
                        local_id=mat.id,
                        external_code=remote.code,
                        last_synced_at=datetime.utcnow(),
                    ))
                    created += 1
        except Exception as e:
            failed += 1
            logger.exception("Failed to sync material %s: %s", remote.code, e)

    job.records_created = created
    job.records_updated = updated
    job.records_failed = failed
    return job
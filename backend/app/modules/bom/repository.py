from __future__ import annotations

from sqlalchemy import delete, select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.bom.models import Bom, BomItem
from app.modules.material.models import Material


class BomRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, bom: Bom) -> Bom:
        self.session.add(bom)
        await self.session.flush()
        return bom

    async def get(self, bom_id: int) -> Bom | None:
        stmt = (
            select(Bom)
            .options(selectinload(Bom.items))
            .where(Bom.id == bom_id)
        )
        return await self.session.scalar(stmt)

    async def get_by_product(self, product_material_id: int, version: str | None = None) -> Bom | None:
        conditions = [Bom.product_material_id == product_material_id]
        if version:
            conditions.append(Bom.version == version)
        else:
            conditions.append(Bom.is_active.is_(True))
        stmt = (
            select(Bom)
            .options(selectinload(Bom.items))
            .where(and_(*conditions))
        )
        return await self.session.scalar(stmt)

    async def list_boms(self, product_material_id: int | None = None, keyword: str | None = None) -> list[Bom]:
        conditions = []
        if product_material_id:
            conditions.append(Bom.product_material_id == product_material_id)
        if keyword:
            conditions.append(func.lower(Bom.version).like(f"%{keyword.lower()}%"))
        stmt = select(Bom).options(selectinload(Bom.items)).where(and_(*conditions)).order_by(Bom.id.desc())
        return list(await self.session.scalars(stmt))

    async def count_items(self, bom_id: int) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(BomItem).where(BomItem.bom_id == bom_id)
        )

    async def ensure_only_one_active(self, product_material_id: int) -> None:
        existing = await self.session.scalar(
            select(Bom).where(
                and_(
                    Bom.product_material_id == product_material_id,
                    Bom.is_active.is_(True),
                )
            )
        )
        if existing:
            existing.is_active = False
            await self.session.flush()

    async def enrich_with_material_info(self, bom: Bom) -> Bom:
        prod = await self.session.get(Material, bom.product_material_id)
        if prod:
            object.__setattr__(bom, "product_code", prod.code)
            object.__setattr__(bom, "product_name", prod.name)
        for item in bom.items:
            comp = await self.session.get(Material, item.component_material_id)
            if comp:
                object.__setattr__(item, "component_code", comp.code)
                object.__setattr__(item, "component_name", comp.name)
        return bom

    async def inventory_available_map(self, component_ids: list[int]) -> dict[int, float]:
        if not component_ids:
            return {}
        from app.modules.material.models import Inventory
        rows = (await self.session.execute(
            select(
                Inventory.material_id,
                func.sum(Inventory.qty_on_hand - Inventory.qty_reserved),
            )
            .where(Inventory.material_id.in_(component_ids))
            .group_by(Inventory.material_id)
        )).all()
        return {int(mid): float(qty) for mid, qty in rows}
"""物料仓储：含库存行级锁查询（SELECT ... FOR UPDATE (of=Inventory)）。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import count_total
from app.core.deps import Pagination
from app.modules.material.models import Inventory, Material, StockTransaction


class MaterialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- 主数据 ----
    async def add_material(self, m: Material) -> Material:
        self.session.add(m)
        await self.session.flush()
        return m

    async def get_material(self, material_id: int) -> Material | None:
        return await self.session.get(Material, material_id)

    async def get_by_code(self, code: str) -> Material | None:
        return await self.session.scalar(select(Material).where(Material.code == code))

    async def list_materials(
        self, mtype: str | None, keyword: str | None, page: Pagination
    ) -> tuple[list[Material], int]:
        stmt = select(Material)
        if mtype:
            stmt = stmt.where(Material.type == mtype)
        if keyword:
            stmt = stmt.where(
                Material.name.ilike(f"%{keyword}%") | Material.code.ilike(f"%{keyword}%")
            )
        stmt = stmt.order_by(Material.id.desc()).offset(page.offset).limit(page.limit)
        rows = list((await self.session.scalars(stmt)).all())
        return rows, await count_total(self.session, stmt)

    # ---- 库存 ----
    async def find_inventory(
        self, material_id: int, batch_no: str, location: str
    ) -> Inventory | None:
        stmt = select(Inventory).where(
            Inventory.material_id == material_id,
            Inventory.batch_no == batch_no,
            Inventory.location == location,
        )
        return await self.session.scalar(stmt)

    async def lock_inventory(
        self, material_id: int, batch_no: str, location: str
    ) -> Inventory | None:
        """行级锁：并发扣减时串行化，防止超扣。

        必须带 of=Inventory，避免把 join 进来的 material 行一并锁定。
        """
        stmt = (
            select(Inventory)
            .where(
                Inventory.material_id == material_id,
                Inventory.batch_no == batch_no,
                Inventory.location == location,
            )
            .with_for_update(of=Inventory)
        )
        return await self.session.scalar(stmt)

    async def add_inventory(self, inv: Inventory) -> Inventory:
        self.session.add(inv)
        await self.session.flush()
        return inv

    async def list_inventory(self, material_id: int | None, page: Pagination):
        stmt = select(Inventory)
        if material_id:
            stmt = stmt.where(Inventory.material_id == material_id)
        stmt = stmt.order_by(Inventory.material_id, Inventory.batch_no)
        stmt = stmt.offset(page.offset).limit(page.limit)
        rows = list((await self.session.scalars(stmt)).all())
        return rows, await count_total(self.session, stmt)

    async def batch_available(self, material_id: int, location: str | None = None):
        """某物料所有批次的可用量合计（用于齐套检查）。"""
        conds = [Inventory.material_id == material_id]
        if location:
            conds.append(Inventory.location == location)
        stmt = select(Inventory).where(*conds)
        rows = list((await self.session.scalars(stmt)).all())
        return sum((r.qty_on_hand - r.qty_reserved) for r in rows)

    # ---- 流水 ----
    async def add_txn(self, txn: StockTransaction) -> None:
        self.session.add(txn)

    async def list_txn(self, material_id: int | None, limit: int = 100):
        stmt = select(StockTransaction)
        if material_id:
            stmt = stmt.where(StockTransaction.material_id == material_id)
        stmt = stmt.order_by(StockTransaction.id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())
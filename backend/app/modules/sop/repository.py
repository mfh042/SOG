"""SOP 仓储。"""
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sop.models import Sop


class SopRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, s: Sop) -> Sop:
        self.session.add(s)
        await self.session.flush()
        return s

    async def get(self, sop_id: int) -> Sop | None:
        return await self.session.get(Sop, sop_id)

    async def get_active_for_op(self, product_code: str, operation_seq: int) -> Sop | None:
        stmt = select(Sop).where(
            and_(
                Sop.product_code == product_code,
                Sop.operation_seq == operation_seq,
                Sop.is_active.is_(True),
            )
        )
        return await self.session.scalar(stmt)

    async def list_by_product(self, product_code: str, active_only: bool = True) -> list[Sop]:
        conds = [Sop.product_code == product_code]
        if active_only:
            conds.append(Sop.is_active.is_(True))
        stmt = select(Sop).where(*conds).order_by(Sop.operation_seq)
        return list((await self.session.scalars(stmt)).all())

    async def list_all(self, keyword: str | None = None, active_only: bool = True) -> list[Sop]:
        stmt = select(Sop)
        if active_only:
            stmt = stmt.where(Sop.is_active.is_(True))
        if keyword:
            stmt = stmt.where(
                Sop.product_code.ilike(f"%{keyword}%")
                | Sop.title.ilike(f"%{keyword}%")
            )
        return list((await self.session.scalars(stmt.order_by(Sop.product_code, Sop.operation_seq))).all())

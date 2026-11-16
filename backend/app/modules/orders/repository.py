"""订单仓储：数据访问，不含业务规则。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import count_total
from app.core.deps import Pagination
from app.modules.orders.models import OrderItem, SalesOrder


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, order: SalesOrder) -> SalesOrder:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get(self, order_id: int) -> SalesOrder | None:
        return await self.session.get(SalesOrder, order_id)

    async def get_by_no(self, order_no: str) -> SalesOrder | None:
        stmt = select(SalesOrder).where(SalesOrder.order_no == order_no)
        return await self.session.scalar(stmt)

    async def list(
        self,
        status: str | None,
        customer: str | None,
        page: Pagination,
    ) -> tuple[list[SalesOrder], int]:
        stmt = select(SalesOrder)
        if status:
            stmt = stmt.where(SalesOrder.status == status)
        if customer:
            stmt = stmt.where(SalesOrder.customer_name.ilike(f"%{customer}%"))
        stmt = stmt.order_by(SalesOrder.id.desc()).offset(page.offset).limit(page.limit)
        rows = list((await self.session.scalars(stmt)).all())
        total = await count_total(self.session, stmt)
        return rows, total

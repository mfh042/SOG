"""生产仓储：工单 / 进度 / 检验 / 追溯。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import count_total
from app.core.deps import Pagination
from app.modules.production.models import (
    ProductionProgress,
    QualityInspection,
    TraceRecord,
    WorkOrder,
)


class ProductionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- 工单 ----
    async def add_wo(self, wo: WorkOrder) -> WorkOrder:
        self.session.add(wo)
        await self.session.flush()
        return wo

    async def get_wo(self, wo_id: int) -> WorkOrder | None:
        return await self.session.get(WorkOrder, wo_id)

    async def lock_wo(self, wo_id: int) -> WorkOrder | None:
        """工单行级锁：报工/报废串行化，防止并发多报（防超产）。"""
        stmt = select(WorkOrder).where(WorkOrder.id == wo_id).with_for_update(of=WorkOrder)
        return await self.session.scalar(stmt)

    async def get_wo_by_no(self, wo_no: str) -> WorkOrder | None:
        return await self.session.scalar(select(WorkOrder).where(WorkOrder.wo_no == wo_no))

    async def list_wo(
        self, status: str | None, product: str | None, page: Pagination
    ) -> tuple[list[WorkOrder], int]:
        stmt = select(WorkOrder)
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        if product:
            stmt = stmt.where(
                WorkOrder.product_code.ilike(f"%{product}%")
                | WorkOrder.product_name.ilike(f"%{product}%")
            )
        stmt = stmt.order_by(WorkOrder.id.desc()).offset(page.offset).limit(page.limit)
        rows = list((await self.session.scalars(stmt)).all())
        return rows, await count_total(self.session, stmt)

    async def list_wo_by_order(self, sales_order_id: int) -> list[WorkOrder]:
        stmt = select(WorkOrder).where(WorkOrder.sales_order_id == sales_order_id)
        return list((await self.session.scalars(stmt.order_by(WorkOrder.id))).all())

    # ---- 进度 ----
    async def add_progress(self, p: ProductionProgress) -> None:
        self.session.add(p)
        await self.session.flush()

    async def find_by_key(self, wo_id: int, key: str) -> ProductionProgress | None:
        stmt = select(ProductionProgress).where(
            ProductionProgress.wo_id == wo_id,
            ProductionProgress.idempotency_key == key,
        )
        return await self.session.scalar(stmt)

    async def list_progress(self, wo_id: int | None, limit: int = 100):
        stmt = select(ProductionProgress)
        if wo_id:
            stmt = stmt.where(ProductionProgress.wo_id == wo_id)
        stmt = stmt.order_by(ProductionProgress.id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def sum_by_operation(self, wo_id: int) -> dict[int | None, tuple]:
        """按工序汇总报工数量，供工序状态机推进使用。"""
        stmt = (
            select(ProductionProgress.seq, ProductionProgress.good_qty, ProductionProgress.bad_qty)
            .where(ProductionProgress.wo_id == wo_id)
        )
        rows = (await self.session.execute(stmt)).all()
        agg: dict[int | None, list] = {}
        for seq, good, bad in rows:
            cur = agg.setdefault(seq, [0, 0])
            cur[0] += good or 0
            cur[1] += bad or 0
        return {k: (v[0], v[1]) for k, v in agg.items()}

    # ---- 质量 ----
    async def add_inspection(self, q: QualityInspection) -> None:
        self.session.add(q)

    async def list_inspection(
        self, wo_id: int | None, product: str | None, page: Pagination
    ) -> tuple[list[QualityInspection], int]:
        stmt = select(QualityInspection)
        if wo_id:
            stmt = stmt.where(QualityInspection.wo_id == wo_id)
        if product:
            stmt = stmt.where(QualityInspection.product_code == product)
        stmt = stmt.order_by(QualityInspection.id.desc()).offset(page.offset).limit(page.limit)
        rows = list((await self.session.scalars(stmt)).all())
        return rows, await count_total(self.session, stmt)

    # ---- 追溯 ----
    async def add_trace(self, t: TraceRecord) -> None:
        self.session.add(t)

    async def list_trace(
        self, wo_id: int | None, limit: int = 200
    ) -> list[TraceRecord]:
        stmt = select(TraceRecord)
        if wo_id:
            stmt = stmt.where(TraceRecord.wo_id == wo_id)
        return list((await self.session.scalars(stmt.order_by(TraceRecord.id.desc()).limit(limit))).all())

    async def trace_by_product(self, batch: str) -> list[TraceRecord]:
        stmt = select(TraceRecord).where(TraceRecord.product_batch == batch)
        return list((await self.session.scalars(stmt.order_by(TraceRecord.id))).all())

    async def trace_by_material(self, batch: str) -> list[TraceRecord]:
        stmt = select(TraceRecord).where(TraceRecord.material_batch == batch)
        return list((await self.session.scalars(stmt.order_by(TraceRecord.id))).all())

    async def trace_by_wo(self, wo_id: int) -> list[TraceRecord]:
        stmt = select(TraceRecord).where(TraceRecord.wo_id == wo_id)
        return list((await self.session.scalars(stmt.order_by(TraceRecord.id))).all())
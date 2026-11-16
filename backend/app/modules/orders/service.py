"""订单业务规则：创建、状态流转（状态机）、乐观锁校验、释放生成工单。"""
import secrets
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import OrderStatus, WorkOrderStatus
from app.core.deps import Pagination
from app.core.exceptions import ConflictException, NotFoundException
from app.modules.material.models import Inventory, Material
from app.modules.material.repository import MaterialRepository
from app.modules.orders.models import OrderItem, SalesOrder
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    OrderCreate,
    OrderItemIn,
    OrderUpdate,
    ReleaseOut,
    ShortageOut,
    WorkOrderDraftOut,
)
from app.modules.production.models import WorkOrder

# 合法状态流转表
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.RELEASED, OrderStatus.CANCELLED},
    OrderStatus.RELEASED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
}

# 允许编辑订单行的状态
EDITABLE_STATUS = (OrderStatus.DRAFT.value, OrderStatus.RELEASED.value)


def _gen_order_no() -> str:
    return f"SO-{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"


def gen_work_order_no(order_no: str, seq: int) -> str:
    """工单号：由订单号派生，便于回溯。WO-{订单号}-{行序号}。"""
    suffix = order_no[3:] if order_no.startswith("SO-") else order_no
    return f"WO-{suffix}-{seq:02d}"


def _item_from(payload: OrderItemIn) -> OrderItem:
    return OrderItem(
        line_no=payload.line_no,
        material_code=payload.material_code,
        material_name=payload.material_name,
        spec=payload.spec,
        qty=payload.qty,
        unit=payload.unit,
    )


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OrderRepository(session)
        self.material_repo = MaterialRepository(session)

    async def create(self, payload: OrderCreate) -> SalesOrder:
        order = SalesOrder(
            order_no=_gen_order_no(),
            customer_name=payload.customer_name,
            product_model=payload.product_model,
            priority=payload.priority,
            planned_date=payload.planned_date,
            note=payload.note,
            status=OrderStatus.DRAFT.value,
        )
        order.items = [_item_from(i) for i in payload.items]
        return await self.repo.add(order)

    async def get(self, order_id: int) -> SalesOrder:
        order = await self.repo.get(order_id)
        if not order:
            raise NotFoundException("订单不存在")
        return order

    async def get_by_no(self, order_no: str) -> SalesOrder:
        order = await self.repo.get_by_no(order_no)
        if not order:
            raise NotFoundException("订单不存在")
        return order

    async def list(self, status: str | None, customer: str | None, page: Pagination):
        return await self.repo.list(status, customer, page)

    async def update(self, order_id: int, payload: OrderUpdate, version: int) -> SalesOrder:
        order = await self.get(order_id)
        if order.status not in EDITABLE_STATUS:
            raise ConflictException("仅草稿或已下达订单可编辑，请先取消释放或新建订单")
        if order.version != version:
            raise ConflictException("订单已被他人修改，请刷新后重试")

        data = payload.model_dump(exclude_unset=True, exclude={"items"})
        for k, v in data.items():
            setattr(order, k, v)
        if payload.items is not None:
            order.items = [_item_from(i) for i in payload.items]
        order.version += 1
        return order

    async def transition(self, order_id: int, target: OrderStatus) -> SalesOrder:
        order = await self.get(order_id)
        current = OrderStatus(order.status)
        if target not in TRANSITIONS[current]:
            raise ConflictException(f"状态 {current.value} 不能流转到 {target.value}")
        order.status = target.value
        order.version += 1
        return order

    async def release(self, order_id: int) -> ReleaseOut:
        """释放订单：按订单行生成工单，并返回缺料告警（不阻断释放）。

        幂等：已释放且有工单时原样返回既有工单；重复调用不会产生第二张工单。
        """
        order = await self.get(order_id)
        current = OrderStatus(order.status)
        existing = await self._existing_work_orders(order.id)
        if existing:
            return ReleaseOut(
                order_no=order.order_no,
                status=order.status,
                version=order.version,
                work_orders=[
                    WorkOrderDraftOut(
                        id=w.id,
                        wo_no=w.wo_no,
                        product_code=w.product_code,
                        product_name=w.product_name,
                        plan_qty=w.plan_qty,
                    )
                    for w in existing
                ],
                warnings=[],
            )
        if current is not OrderStatus.DRAFT:
            raise ConflictException(f"状态 {current.value} 不可释放")

        warnings = await self._check_shortage(order)
        created: List[WorkOrder] = []
        for idx, item in enumerate(sorted(order.items, key=lambda i: i.line_no), start=1):
            wo = WorkOrder(
                wo_no=gen_work_order_no(order.order_no, idx),
                sales_order_id=order.id,
                product_code=item.material_code,
                product_name=item.material_name,
                plan_qty=item.qty,
                status=WorkOrderStatus.PLANNED.value,
            )
            self.session.add(wo)
            created.append(wo)

        await self.session.flush()
        order.status = OrderStatus.RELEASED.value
        order.version += 1
        return ReleaseOut(
            order_no=order.order_no,
            status=order.status,
            version=order.version,
            work_orders=[
                WorkOrderDraftOut(
                    id=w.id,
                    wo_no=w.wo_no,
                    product_code=w.product_code,
                    product_name=w.product_name,
                    plan_qty=w.plan_qty,
                )
                for w in created
            ],
            warnings=warnings,
        )

    async def list_work_orders(self, order_id: int) -> List[WorkOrder]:
        """订单关联工单（释放后由订单派生，供订单详情页联动展示）。"""
        await self.get(order_id)
        return await self._existing_work_orders(order_id)

    async def _existing_work_orders(self, order_id: int) -> List[WorkOrder]:
        stmt = select(WorkOrder).where(WorkOrder.sales_order_id == order_id)
        return list((await self.session.scalars(stmt)).all())

    async def _check_shortage(self, order: SalesOrder) -> List[ShortageOut]:
        """按订单行匹配同名物料，汇总可用量并给出缺料清单。

        未建物料主数据的订单行不参与齐套判断（视为外部自制件）。
        """
        required: dict[str, dict] = {}
        for item in order.items:
            key = item.material_code
            entry = required.setdefault(
                key, {"name": item.material_name, "qty": Decimal(0)}
            )
            entry["qty"] += item.qty

        warnings: List[ShortageOut] = []
        for code, info in required.items():
            material = await self.material_repo.get_by_code(code)
            if not material:
                continue
            available = await self.material_repo.batch_available(material.id)
            if available < info["qty"]:
                warnings.append(
                    ShortageOut(
                        material_code=code,
                        material_name=info["name"],
                        required=info["qty"],
                        available=available,
                        shortage=info["qty"] - available,
                    )
                )
        return warnings

    async def product_availability(self, material_code: str) -> Decimal:
        """仅供内部/看板使用：某物料可用量合计。"""
        material = await self.material_repo.get_by_code(material_code)
        if not material:
            return Decimal(0)
        stmt = select(Inventory).where(Inventory.material_id == material.id)
        rows = list((await self.session.scalars(stmt)).all())
        return sum((r.qty_on_hand - r.qty_reserved for r in rows), Decimal(0))

    async def material_map(self) -> dict[str, Material]:
        stmt = select(Material)
        return {m.code: m for m in (await self.session.scalars(stmt)).all()}
"""订单业务规则：创建、状态流转（状态机）、乐观锁校验、释放生成工单、BOM 驱动齐套检查。"""
import secrets
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import OrderStatus, WorkOrderStatus
from app.core.deps import Pagination
from app.core.exceptions import ConflictException, NotFoundException
from app.modules.bom.repository import BomRepository
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
    OrderStatus.DRAFT: {OrderStatus.RELEASED, OrderStatus.CANCELLED, OrderStatus.LOCKED},
    OrderStatus.RELEASED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED, OrderStatus.LOCKED},
    OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.LOCKED},
    OrderStatus.COMPLETED: {OrderStatus.CLOSED, OrderStatus.LOCKED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.LOCKED: {OrderStatus.DRAFT, OrderStatus.RELEASED},
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
        self.bom_repo = BomRepository(session)

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
        await self.repo.add(order)
        await self.session.commit()
        return order

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
        await self.session.commit()
        return order

    async def transition(self, order_id: int, target: OrderStatus) -> SalesOrder:
        order = await self.get(order_id)
        current = OrderStatus(order.status)
        if target not in TRANSITIONS[current]:
            raise ConflictException(f"状态 {current.value} 不能流转到 {target.value}")
        order.status = target.value
        order.version += 1
        await self.session.commit()
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
        await self.session.commit()
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
        """BOM 驱动的齐套检查：订单行成品 → 激活 BOM → 组件需求展开 → 对比库存。

        三条路径：
        1. 成品物料存在且有激活 BOM → 展开所有组件需求（含损耗率），逐项对比可用量
        2. 成品物料存在但无 BOM → 标记 KIT_UNKNOWN（提示补建 BOM），仍按成品直查库存兜底
        3. 成品物料不存在（外部自制件）→ 跳过，不参与齐套判断

        返回的 warnings 可能同时包含组件级缺口和 KIT_UNKNOWN 提示。
        """
        warnings: List[ShortageOut] = []
        component_summary: dict[int, dict] = {}

        for item in order.items:
            product = await self.material_repo.get_by_code(item.material_code)
            if product is None:
                continue

            bom = await self.bom_repo.get_by_product(product.id)
            if bom is None:
                available = await self.material_repo.batch_available(product.id)
                if available < item.qty:
                    warnings.append(
                        ShortageOut(
                            material_code=item.material_code,
                            material_name=f"{item.material_name}（未建 BOM，按成品直查）",
                            required=item.qty,
                            available=available,
                            shortage=item.qty - available,
                        )
                    )
                else:
                    warnings.append(
                        ShortageOut(
                            material_code=item.material_code,
                            material_name=f"{item.material_name}（KIT_UNKNOWN：未建 BOM）",
                            required=item.qty,
                            available=available,
                            shortage=Decimal(0),
                        )
                    )
                continue

            for bom_item in bom.items:
                need = Decimal(str(bom_item.qty)) * item.qty * (
                    Decimal("1") + Decimal(str(bom_item.loss_rate))
                )
                entry = component_summary.setdefault(
                    bom_item.component_material_id,
                    {"need": Decimal(0), "name": "", "code": ""},
                )
                entry["need"] += need
                if not entry["code"]:
                    comp = await self.material_repo.get_material(bom_item.component_material_id)
                    if comp:
                        entry["code"] = comp.code
                        entry["name"] = comp.name

        if component_summary:
            comp_ids = list(component_summary.keys())
            avail_map = await self.bom_repo.inventory_available_map(comp_ids)
            for comp_id, info in component_summary.items():
                available = Decimal(str(avail_map.get(comp_id, 0.0)))
                need = info["need"].quantize(Decimal("0.0001"))
                shortage = (need - available).quantize(Decimal("0.0001"))
                if shortage > 0:
                    warnings.append(
                        ShortageOut(
                            material_code=info["code"] or f"ID:{comp_id}",
                            material_name=info["name"],
                            required=need,
                            available=available,
                            shortage=shortage,
                        )
                    )

        return warnings

    async def kit_check(self, order_id: int) -> dict:
        """订单级齐套检查（独立接口）：返回 kit_status + 缺料清单。"""
        order = await self.get(order_id)
        warnings = await self._check_shortage(order)

        has_shortage = any(w.shortage > 0 for w in warnings)
        has_unknown = any("KIT_UNKNOWN" in w.material_name for w in warnings)

        if has_shortage:
            status = "KIT_SHORT"
        elif has_unknown:
            status = "KIT_UNKNOWN"
        else:
            status = "KIT_READY"

        return {
            "order_id": order.id,
            "order_no": order.order_no,
            "status": status,
            "shortage_count": sum(1 for w in warnings if w.shortage > 0),
            "unknown_count": sum(1 for w in warnings if "KIT_UNKNOWN" in w.material_name),
            "details": warnings,
        }

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

    async def split(self, order_id: int, split_qty: Decimal) -> SalesOrder:
        """订单拆分：从前 N 台拆出为新订单，原订单扣减数量。"""
        order = await self.get(order_id)
        if order.status not in (OrderStatus.DRAFT.value, OrderStatus.RELEASED.value):
            raise ConflictException("仅草稿或已下达订单可拆分")
        total = sum((i.qty for i in order.items), Decimal(0))
        if split_qty <= 0 or split_qty >= total:
            raise ConflictException(f"拆分数量必须在 (0, {total}) 之间")

        new_order = SalesOrder(
            order_no=_gen_order_no(),
            customer_name=order.customer_name,
            product_model=order.product_model,
            priority=order.priority,
            planned_date=order.planned_date,
            note=f"拆分自 {order.order_no}",
            status=order.status,
        )
        remaining = split_qty
        for item in sorted(order.items, key=lambda i: i.line_no):
            take = min(item.qty, remaining)
            if take > 0:
                new_order.items.append(
                    OrderItem(
                        line_no=item.line_no,
                        material_code=item.material_code,
                        material_name=item.material_name,
                        spec=item.spec,
                        qty=take,
                        unit=item.unit,
                    )
                )
                item.qty -= take
                remaining -= take
            if remaining <= 0:
                break

        new_order.version = 1
        order.version += 1
        self.session.add(new_order)
        await self.session.commit()
        return new_order

    async def reschedule(self, order_id: int, planned_date: str) -> SalesOrder:
        from datetime import date
        order = await self.get(order_id)
        if order.status in (OrderStatus.CANCELLED.value, OrderStatus.CLOSED.value, OrderStatus.LOCKED.value):
            raise ConflictException("当前状态不可排产")
        order.planned_date = date.fromisoformat(planned_date)
        order.version += 1
        await self.session.commit()
        return order

    async def adjust_qty(self, order_id: int, qty: float) -> SalesOrder:
        order = await self.get(order_id)
        if order.status not in EDITABLE_STATUS:
            raise ConflictException("仅草稿或已下达订单可调整数量")
        decimal_qty = Decimal(str(qty))
        total = sum((i.qty for i in order.items), Decimal(0))
        if total <= 0:
            raise ConflictException("订单行数量异常")
        ratio = decimal_qty / total
        for item in order.items:
            item.qty = (item.qty * ratio).quantize(Decimal("0.001"))
        order.version += 1
        await self.session.commit()
        return order

    async def batch_release(self, order_ids: List[int]) -> dict:
        ok, fail = 0, 0
        for oid in order_ids:
            try:
                await self.release(oid)
                ok += 1
            except Exception:
                fail += 1
        return {"ok": ok, "fail": fail}

    async def import_orders(self, rows: List[dict]) -> dict:
        created, failed = 0, 0
        errors: List[dict] = []
        for idx, raw in enumerate(rows, start=2):
            try:
                order = SalesOrder(
                    order_no=_gen_order_no(),
                    customer_name=(raw.get("客户") or raw.get("customer") or "导入").strip(),
                    product_model=(raw.get("产品型号") or raw.get("product_model") or "").strip(),
                    priority=int(raw.get("优先级") or raw.get("priority") or 3),
                    note=f"CSV 导入 行{idx}",
                    status=OrderStatus.DRAFT.value,
                )
                if raw.get("计划日期") or raw.get("planned_date"):
                    from datetime import date
                    order.planned_date = date.fromisoformat(
                        (raw.get("计划日期") or raw.get("planned_date")).strip()
                    )
                order.items = [
                    OrderItem(
                        line_no=1,
                        material_code=order.product_model,
                        material_name=order.product_model,
                        qty=Decimal(str(raw.get("数量") or raw.get("qty") or 1)),
                        unit=(raw.get("单位") or raw.get("unit") or "PCS").strip() or "PCS",
                    )
                ]
                self.session.add(order)
                created += 1
            except Exception as e:
                failed += 1
                errors.append({"row": idx, "error": str(e)})
        await self.session.commit()
        return {"created": created, "failed": failed, "errors": errors}
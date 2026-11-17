"""生产业务：工单状态机、工序路由、工序级报工、末道入库、报废、质量、正反向追溯。

并发与一致性：
- 工单变更统一走 lock_wo（SELECT ... FOR UPDATE of=WorkOrder），报工串行化，避免并发超产；
- 报工支持 idempotency_key，同键重复提交仅生效一次（返回 duplicated=True）；
- 末道工序报工合格品自动入成品仓，批次 FG-{工单号}-{日期}，复用物料模块行级锁。
"""
import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import (
    QualityResult,
    TraceEventType,
    WorkOrderStatus,
)
from app.core.deps import Pagination
from app.core.exceptions import ConflictException, NotFoundException
from app.modules.material.models import Material
from app.modules.material.repository import MaterialRepository
from app.modules.material.schemas import StockIn, StockOpReq
from app.modules.material.service import MaterialService
from app.modules.production.models import (
    ProductionProgress,
    QualityInspection,
    TraceRecord,
    WorkOrder,
)
from app.modules.production.repository import ProductionRepository
from app.modules.production.schemas import (
    InspectionIn,
    OperationStep,
    ReportOut,
    ReportReq,
    ScrapReq,
    WorkOrderCreate,
    WorkOrderOut,
    WorkOrderUpdate,
)

WO_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.PLANNED: {WorkOrderStatus.RELEASED, WorkOrderStatus.SCRAPPED},
    WorkOrderStatus.RELEASED: {WorkOrderStatus.RUNNING, WorkOrderStatus.SCRAPPED},
    WorkOrderStatus.RUNNING: {WorkOrderStatus.DONE, WorkOrderStatus.SCRAPPED},
    WorkOrderStatus.DONE: set(),
    WorkOrderStatus.SCRAPPED: set(),
}

# 默认工艺路线（未显式传 route 时使用）
DEFAULT_ROUTE = [
    {"seq": 1, "name": "上料", "station": "ST-01"},
    {"seq": 2, "name": "装配", "station": "ST-02"},
    {"seq": 3, "name": "拧紧", "station": "ST-03"},
    {"seq": 4, "name": "检验", "station": "ST-04"},
    {"seq": 5, "name": "包装入库", "station": "ST-05"},
]

FINISHED_LOCATION = "FG-01"
WIP_LOCATION = "WH-01"


def _gen_wo_no() -> str:
    return f"WO-{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"


def finished_batch_no(wo_no: str) -> str:
    return f"FG-{wo_no}-{datetime.now():%Y%m%d}"


def _normalize_route(route: list[dict]) -> list[dict]:
    """标准化工艺路线：补齐 seq/status，按 seq 升序。"""
    if not route:
        route = [dict(r) for r in DEFAULT_ROUTE]
    steps: list[dict] = []
    for idx, raw in enumerate(route, start=1):
        steps.append(
            {
                "seq": int(raw.get("seq") or idx),
                "name": raw.get("name") or f"工序{idx}",
                "station": raw.get("station"),
                "status": raw.get("status") or "pending",
                "good_qty": raw.get("good_qty", 0),
                "bad_qty": raw.get("bad_qty", 0),
                "started_at": raw.get("started_at"),
                "finished_at": raw.get("finished_at"),
            }
        )
    return sorted(steps, key=lambda s: s["seq"])


class ProductionService:
    def __init__(self, session: AsyncSession, operator: str = "system"):
        self.session = session
        self.operator = operator
        self.repo = ProductionRepository(session)
        self.material_repo = MaterialRepository(session)
        self.material_service = MaterialService(session, operator)

    # ---------- 工单 ----------
    async def create_wo(self, payload: WorkOrderCreate) -> WorkOrder:
        wo = WorkOrder(
            wo_no=_gen_wo_no(),
            sales_order_id=payload.sales_order_id,
            product_code=payload.product_code,
            product_name=payload.product_name,
            plan_qty=payload.plan_qty,
            line=payload.line,
            station=payload.station,
            route=_normalize_route(payload.route),
            planned_start=payload.planned_start,
            planned_end=payload.planned_end,
            status=WorkOrderStatus.PLANNED.value,
        )
        await self.repo.add_wo(wo)
        await self.session.commit()
        return wo

    async def get_wo(self, wo_id: int) -> WorkOrder:
        wo = await self.repo.get_wo(wo_id)
        if not wo:
            raise NotFoundException("工单不存在")
        return wo

    async def list_wo(self, status, product, page: Pagination):
        return await self.repo.list_wo(status, product, page)

    async def list_by_order(self, sales_order_id: int):
        return await self.repo.list_wo_by_order(sales_order_id)

    async def update_wo(self, wo_id: int, payload: WorkOrderUpdate, version: int) -> WorkOrder:
        wo = await self.get_wo(wo_id)
        if wo.status not in (WorkOrderStatus.PLANNED.value, WorkOrderStatus.RELEASED.value):
            raise ConflictException("仅计划或已下达工单可修改")
        if wo.version != version:
            raise ConflictException("工单已被他人修改，请刷新后重试")
        data = payload.model_dump(exclude_unset=True)
        if "route" in data and data["route"] is not None:
            data["route"] = _normalize_route(data["route"])
        if "plan_qty" in data and data["plan_qty"] is not None:
            if data["plan_qty"] < wo.done_qty + wo.scrap_qty:
                raise ConflictException("计划数量不得小于已完工 + 报废数量")
        for k, v in data.items():
            setattr(wo, k, v)
        wo.version += 1
        await self.session.commit()
        return wo

    async def transition(self, wo_id: int, target: WorkOrderStatus) -> WorkOrder:
        wo = await self.repo.lock_wo(wo_id)
        if not wo:
            raise NotFoundException("工单不存在")
        current = WorkOrderStatus(wo.status)
        if target not in WO_TRANSITIONS[current]:
            raise ConflictException(f"工单 {current.value} 不能流转到 {target.value}")
        wo.status = target.value
        if target is WorkOrderStatus.RUNNING:
            route = _normalize_route(wo.route)
            if route and route[0]["status"] == "pending":
                route[0]["status"] = "in_progress"
                route[0]["started_at"] = datetime.now().isoformat()
            wo.route = route
            await self.repo.add_trace(
                TraceRecord(
                    wo_id=wo.id,
                    event_type=TraceEventType.WORK_START.value,
                    operator=self.operator,
                    detail={"wo_no": wo.wo_no, "route": [r["name"] for r in route]},
                )
            )
        wo.version += 1
        await self.session.commit()
        return wo

    # ---------- 工序 ----------
    async def operations(self, wo_id: int) -> list[OperationStep]:
        wo = await self.get_wo(wo_id)
        route = _normalize_route(wo.route)
        agg = await self.repo.sum_by_operation(wo.id)
        steps: list[OperationStep] = []
        for r in route:
            good, bad = agg.get(r["seq"], (Decimal(0), Decimal(0)))
            status = r["status"]
            if good >= wo.plan_qty and status != "completed":
                status = "completed"
            steps.append(
                OperationStep(
                    seq=r["seq"],
                    name=r["name"],
                    station=r.get("station"),
                    status=status,
                    good_qty=good,
                    bad_qty=bad,
                    started_at=r.get("started_at"),
                    finished_at=r.get("finished_at"),
                )
            )
        return steps

    def _pick_operation(self, route: list[dict], seq: int | None) -> dict:
        """选择本次报工的工序：指定 seq 则用之，否则取第一个未完成工序。"""
        if seq is not None:
            for r in route:
                if r["seq"] == seq:
                    return r
            raise ConflictException(f"工序 {seq} 不在当前工艺路线中")
        for r in route:
            if r["status"] != "completed":
                return r
        raise ConflictException("所有工序均已完成，无需报工")

    # ---------- 报工 ----------
    async def report(self, wo_id: int, payload: ReportReq) -> ReportOut:
        if payload.idempotency_key:
            dup = await self.repo.find_by_key(wo_id, payload.idempotency_key)
            if dup:
                wo = await self.get_wo(wo_id)
                return ReportOut(
                    work_order=WorkOrderOut.model_validate(wo, from_attributes=True),
                    duplicated=True,
                )

        wo = await self.repo.lock_wo(wo_id)
        if not wo:
            raise NotFoundException("工单不存在")
        if wo.status != WorkOrderStatus.RUNNING.value:
            raise ConflictException("仅生产中工单可报工")

        route = _normalize_route(wo.route)
        op = self._pick_operation(route, payload.seq)
        agg = await self.repo.sum_by_operation(wo.id)
        op_done = agg.get(op["seq"], (Decimal(0), Decimal(0)))[0]
        if op_done + payload.good_qty + wo.scrap_qty > wo.plan_qty:
            raise ConflictException(
                f"报工数量超出工单计划数量：工序 {op['seq']} 已完工 {op_done} + 报废 {wo.scrap_qty} + 本次 {payload.good_qty} > 计划 {wo.plan_qty}"
            )

        if op["status"] == "pending":
            op["status"] = "in_progress"
            op["started_at"] = datetime.now().isoformat()

        await self.repo.add_progress(
            ProductionProgress(
                wo_id=wo.id,
                seq=op["seq"],
                good_qty=payload.good_qty,
                bad_qty=payload.bad_qty,
                station=payload.station or op.get("station") or wo.station,
                operator=self.operator,
                note=payload.note,
                idempotency_key=payload.idempotency_key,
            )
        )
        consumed: list[dict] = []
        for use in payload.materials:
            detail: list[dict] = []
            await self.material_service.consume(
                StockOpReq(
                    material_id=use.material_id,
                    batch_no=use.batch_no,
                    location=use.location,
                    qty=use.qty,
                    ref_type="WORK_ORDER",
                    ref_id=wo.id,
                    remark=f"工单 {wo.wo_no} 工序 {op['seq']} 领料",
                ),
                consumed=detail,
            )
            consumed.extend(detail)

        for c in consumed:
            await self.repo.add_trace(
                TraceRecord(
                    wo_id=wo.id,
                    product_batch=payload.product_batch,
                    material_batch=c["batch_no"],
                    event_type=TraceEventType.ISSUE_MATERIAL.value,
                    qty=c["qty"],
                    operator=self.operator,
                    detail={
                        "wo_no": wo.wo_no,
                        "seq": op["seq"],
                        "operation": op["name"],
                        "location": c["location"],
                    },
                )
            )

        await self.repo.add_trace(
            TraceRecord(
                wo_id=wo.id,
                product_batch=payload.product_batch,
                event_type=TraceEventType.ASSEMBLE.value,
                qty=payload.good_qty,
                operator=self.operator,
                detail={
                    "wo_no": wo.wo_no,
                    "product_code": wo.product_code,
                    "seq": op["seq"],
                    "operation": op["name"],
                    "station": payload.station or op.get("station"),
                    "bad_qty": str(payload.bad_qty),
                    "material_batches": [c["batch_no"] for c in consumed],
                },
            )
        )

        agg = await self.repo.sum_by_operation(wo.id)
        for step in route:
            done, bad = agg.get(step["seq"], (Decimal(0), Decimal(0)))
            step["good_qty"] = float(done)
            step["bad_qty"] = float(bad)
        cur_good = agg.get(op["seq"], (Decimal(0), Decimal(0)))[0]
        if cur_good >= wo.plan_qty:
            op["status"] = "completed"
            op["finished_at"] = op.get("finished_at") or datetime.now().isoformat()

        finished = False
        finished_qty = Decimal(0)
        finished_batch: str | None = None
        is_last = op["seq"] == route[-1]["seq"]
        last_good = agg.get(route[-1]["seq"], (Decimal(0), Decimal(0)))[0]
        if is_last:
            wo.done_qty = last_good
        if is_last and last_good >= wo.plan_qty:
            finished = True
            finished_qty = last_good
            finished_batch = payload.product_batch or finished_batch_no(wo.wo_no)
            await self._finish_into_finished(wo, finished_qty, finished_batch)
            wo.status = WorkOrderStatus.DONE.value
            if op["status"] != "completed":
                op["status"] = "completed"
                op["finished_at"] = datetime.now().isoformat()

        wo.route = route
        wo.version += 1
        await self.session.commit()
        return ReportOut(
            work_order=WorkOrderOut.model_validate(wo, from_attributes=True),
            finished=finished,
            finished_qty=finished_qty,
            finished_batch=finished_batch,
        )

    async def _finish_into_finished(
        self, wo: WorkOrder, qty: Decimal, batch: str
    ) -> None:
        """末道完工入库：按产品编码匹配成品物料，找不到则自动建档后入库。"""
        material = await self.material_repo.get_by_code(wo.product_code)
        if material is None:
            material = Material(
                code=wo.product_code,
                name=wo.product_name,
                type="FINISHED",
                unit="PCS",
            )
            self.session.add(material)
            await self.session.flush()

        await self.material_service.inbound(
            StockIn(
                material_id=material.id,
                batch_no=batch,
                location=FINISHED_LOCATION,
                qty=qty,
                remark=f"工单完工入库 {wo.wo_no}",
            )
        )
        await self.repo.add_trace(
            TraceRecord(
                wo_id=wo.id,
                product_batch=batch,
                material_id=material.id,
                event_type=TraceEventType.PACK.value,
                qty=qty,
                operator=self.operator,
                detail={"wo_no": wo.wo_no, "location": FINISHED_LOCATION},
            )
        )

    # ---------- 报废 ----------
    async def scrap(self, wo_id: int, payload: ScrapReq) -> WorkOrder:
        wo = await self.repo.lock_wo(wo_id)
        if not wo:
            raise NotFoundException("工单不存在")
        if wo.status != WorkOrderStatus.RUNNING.value:
            raise ConflictException("仅生产中工单可报废")
        if wo.done_qty + wo.scrap_qty + payload.qty > wo.plan_qty:
            raise ConflictException("报废数量超出工单计划数量")
        wo.scrap_qty += payload.qty
        await self.repo.add_trace(
            TraceRecord(
                wo_id=wo.id,
                event_type=TraceEventType.SCRAP.value,
                qty=payload.qty,
                operator=self.operator,
                detail={"wo_no": wo.wo_no, "note": payload.note, "seq": payload.seq},
            )
        )
        wo.version += 1
        return wo

    # ---------- 进度 ----------
    async def list_progress(self, wo_id: int | None, limit: int = 100):
        return await self.repo.list_progress(wo_id, limit)

    # ---------- 质量 ----------
    async def add_inspection(self, payload: InspectionIn) -> QualityInspection:
        if payload.result not in [r.value for r in QualityResult]:
            raise ConflictException("检验结果非法")
        q = QualityInspection(
            wo_id=payload.wo_id,
            product_code=payload.product_code,
            product_batch=payload.product_batch,
            inspect_type=payload.inspect_type,
            operation_seq=payload.operation_seq,
            sample_qty=payload.sample_qty,
            inspect_item=payload.inspect_item,
            result=payload.result,
            defect_code=payload.defect_code,
            defect_desc=payload.defect_desc,
            defect_images=payload.defect_images,
            inspector=payload.inspector or self.operator,
            judge=payload.judge,
            note=payload.note,
        )
        await self.repo.add_inspection(q)
        await self.session.flush()
        await self.repo.add_trace(
            TraceRecord(
                wo_id=payload.wo_id,
                product_batch=payload.product_batch,
                event_type=TraceEventType.INSPECT.value,
                qty=Decimal(1),
                operator=q.inspector,
                detail={
                    "result": payload.result,
                    "defect_code": payload.defect_code,
                    "product_code": payload.product_code,
                    "inspect_item": payload.inspect_item,
                },
            )
        )
        return q

    async def list_inspection(self, wo_id, product, page: Pagination):
        return await self.repo.list_inspection(wo_id, product, page)

    async def quality_stats(self) -> dict:
        stmt = select(QualityInspection.result, func.count()).group_by(QualityInspection.result)
        by_result = {r: int(c) for r, c in (await self.session.execute(stmt)).all()}
        total = sum(by_result.values())
        pass_qty = by_result.get(QualityResult.PASS.value, 0)
        sr = round(pass_qty / total * 100, 2) if total else None
        dstmt = (
            select(QualityInspection.defect_code, func.count().label("cnt"))
            .where(QualityInspection.defect_code.is_not(None))
            .group_by(QualityInspection.defect_code)
            .order_by(func.count().desc())
            .limit(10)
        )
        defects = (await self.session.execute(dstmt)).all()
        return {
            "total": total,
            "by_result": by_result,
            "pass_rate": sr,
            "top_defects": [{"code": code, "count": int(cnt)} for code, cnt in defects],
        }

    # ---------- 追溯 ----------
    async def list_trace(self, wo_id: int | None, limit: int = 200):
        return await self.repo.list_trace(wo_id, limit)

    async def forward_trace(self, product_batch: str) -> list[TraceRecord]:
        return await self.repo.trace_by_product(product_batch)

    async def backward_trace(self, material_batch: str) -> list[TraceRecord]:
        records = await self.repo.trace_by_material(material_batch)
        wo_ids = {r.wo_id for r in records if r.wo_id}
        if not wo_ids:
            return records
        extra: list[TraceRecord] = []
        for wid in wo_ids:
            extra.extend(await self.repo.trace_by_wo(wid))
        seen = {r.id for r in records}
        merged = records + [r for r in extra if r.id not in seen]
        return sorted(merged, key=lambda r: r.id)

    async def trace_tree(self, product_batch: str) -> dict:
        """成品批次 → 关联工单 → 该工单全部事件（正向扩散的树形结构）。"""
        records = await self.repo.trace_by_product(product_batch)
        wo_ids = sorted({r.wo_id for r in records if r.wo_id})
        nodes = []
        for wid in wo_ids:
            events = await self.repo.trace_by_wo(wid)
            wo = await self.repo.get_wo(wid)
            nodes.append(
                {
                    "wo_id": wid,
                    "wo_no": wo.wo_no if wo else None,
                    "product_code": wo.product_code if wo else None,
                    "status": wo.status if wo else None,
                    "events": [
                        {
                            "event_type": e.event_type,
                            "material_batch": e.material_batch,
                            "product_batch": e.product_batch,
                            "qty": str(e.qty),
                            "detail": e.detail,
                            "created_at": e.created_at,
                        }
                        for e in events
                    ],
                }
            )
        return {"product_batch": product_batch, "work_orders": nodes}

    async def trace_bfs(self, product_batch: str, max_depth: int = 4) -> dict:
        """反向 BFS：成品批次 → 逐层展开原料来源，最多 max_depth 层。

        典型路径：成品批次 → 末道 WO → 领料原料批次 → 上一层 WO（半成品）→ 更上层原料...
        每层收集当前工单消耗的所有原料批次，递归查找这些原料还被哪些工单生产过。
        """
        visited_wos: set[int] = set()
        visited_materials: set[str] = set()
        visited_products: set[str] = {product_batch}
        layers: list[dict] = []

        current_products = [product_batch]
        for depth in range(max_depth):
            product_records = await self.repo.trace_by_products(current_products)
            current_wo_ids = sorted(
                {r.wo_id for r in product_records if r.wo_id and r.wo_id not in visited_wos}
            )
            if not current_wo_ids:
                break
            visited_wos.update(current_wo_ids)

            wo_nodes = []
            next_materials: set[str] = set()
            for wid in current_wo_ids:
                wo = await self.repo.get_wo(wid)
                events = await self.repo.trace_by_wo(wid)
                materials_used = sorted(
                    {e.material_batch for e in events if e.material_batch and e.material_batch not in visited_materials}
                )
                visited_materials.update(materials_used)
                next_materials.update(materials_used)

                wo_nodes.append(
                    {
                        "wo_id": wid,
                        "wo_no": wo.wo_no if wo else None,
                        "product_code": wo.product_code if wo else None,
                        "status": wo.status if wo else None,
                        "events": [
                            {
                                "event_type": e.event_type,
                                "material_batch": e.material_batch,
                                "product_batch": e.product_batch,
                                "qty": str(e.qty),
                            }
                            for e in events
                        ],
                        "material_batches": materials_used,
                    }
                )

            layers.append({"depth": depth, "work_orders": wo_nodes})

            material_records = await self.repo.trace_by_materials(list(next_materials))
            next_products = sorted(
                {
                    r.product_batch
                    for r in material_records
                    if r.product_batch and r.product_batch not in visited_products
                }
            )
            visited_products.update(next_products)
            if not next_products:
                break
            current_products = next_products

        return {
            "product_batch": product_batch,
            "max_depth": max_depth,
            "layers": layers,
            "total_wos": len(visited_wos),
            "total_material_batches": len(visited_materials),
        }

    async def wip_summary(self) -> dict:
        stmt = select(WorkOrder).where(WorkOrder.status.in_(
            [WorkOrderStatus.RELEASED.value, WorkOrderStatus.RUNNING.value]
        ))
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        now = datetime.now()
        total = len(rows)
        total_plan = sum(float(r.plan_qty) for r in rows)
        total_done = sum(float(r.done_qty) for r in rows)
        avg_rate = (total_done / total_plan * 100) if total_plan else 0

        station_map = {}
        for r in rows:
            s = r.station or "未分配"
            item = station_map.setdefault(s, {"station": s, "wo_count": 0, "plan_qty": 0.0, "done_qty": 0.0, "aging_hours_sum": 0.0})
            item["wo_count"] += 1
            item["plan_qty"] += float(r.plan_qty)
            item["done_qty"] += float(r.done_qty)
            if r.planned_start:
                item["aging_hours_sum"] += (now - r.planned_start).total_seconds() / 3600

        stations = []
        for s, v in station_map.items():
            v["wip_qty"] = round(v["plan_qty"] - v["done_qty"], 3)
            v["avg_aging_hours"] = round(v["aging_hours_sum"] / v["wo_count"], 1) if v["wo_count"] else 0
            v["done_rate"] = round(v["done_qty"] / v["plan_qty"] * 100, 1) if v["plan_qty"] else 0
            del v["aging_hours_sum"]
            stations.append(v)
        stations.sort(key=lambda x: x["wip_qty"], reverse=True)

        bottleneck = stations[0] if stations else None

        aging_threshold = 24.0
        aging_rows = []
        for r in rows:
            if r.planned_start:
                h = (now - r.planned_start).total_seconds() / 3600
                if h > aging_threshold:
                    aging_rows.append({
                        "wo_id": r.id,
                        "wo_no": r.wo_no,
                        "product_code": r.product_code,
                        "product_name": r.product_name,
                        "station": r.station,
                        "plan_qty": float(r.plan_qty),
                        "done_qty": float(r.done_qty),
                        "wip_qty": round(float(r.plan_qty) - float(r.done_qty), 3),
                        "aging_hours": round(h, 1),
                        "status": r.status,
                    })
        aging_rows.sort(key=lambda x: x["aging_hours"], reverse=True)

        return {
            "total_wip_wo": total,
            "total_plan_qty": round(total_plan, 3),
            "total_done_qty": round(total_done, 3),
            "wip_qty": round(total_plan - total_done, 3),
            "avg_done_rate": round(avg_rate, 1),
            "bottleneck_station": bottleneck["station"] if bottleneck else None,
            "bottleneck_wip_qty": bottleneck["wip_qty"] if bottleneck else 0,
            "overdue_wip_count": len(aging_rows),
            "stations": stations,
            "aging_wips": aging_rows,
        }
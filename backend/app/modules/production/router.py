"""生产 / 质量 / 追溯 REST 路由。"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import WorkOrderStatus
from app.core.deps import Pagination, get_db, get_pagination
from app.core.response import PageData, Resp
from app.modules.production.schemas import (
    InspectionIn,
    InspectionOut,
    OperationStep,
    ReportOut,
    ReportReq,
    ScrapReq,
    TraceOut,
    WorkOrderCreate,
    WorkOrderOut,
    WorkOrderUpdate,
)
from app.modules.production.service import ProductionService

router = APIRouter(prefix="/api/production", tags=["生产执行"])


def _svc(session: AsyncSession, operator: str) -> ProductionService:
    return ProductionService(session, operator)


def _wo(o) -> WorkOrderOut:
    return WorkOrderOut.model_validate(o, from_attributes=True)


@router.post("/work-orders", response_model=Resp[WorkOrderOut], summary="创建工单")
async def create_wo(
    payload: WorkOrderCreate,
    operator: str = Header("system", alias="X-Operator"),
    session: AsyncSession = Depends(get_db),
):
    wo = await _svc(session, operator).create_wo(payload)
    return Resp.ok(_wo(wo), message="工单已创建")


@router.get("/work-orders", response_model=Resp[PageData[WorkOrderOut]], summary="工单分页列表")
async def list_wo(
    status: str | None = Query(None, description="PLANNED/RELEASED/RUNNING/DONE/SCRAPPED"),
    product: str | None = Query(None, description="产品编码或名称模糊匹配"),
    page: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await _svc(session, "system").list_wo(status, product, page)
    return Resp.page([_wo(r) for r in rows], total, page.page, page.size)


@router.get("/work-orders/{wo_id}", response_model=Resp[WorkOrderOut], summary="工单详情")
async def get_wo(wo_id: int, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_wo(await _svc(session, "system").get_wo(wo_id)))


@router.put("/work-orders/{wo_id}", response_model=Resp[WorkOrderOut], summary="编辑工单（乐观锁）")
async def update_wo(
    wo_id: int,
    payload: WorkOrderUpdate,
    version: int = Query(..., description="乐观锁版本号"),
    operator: str = Header("system", alias="X-Operator"),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_wo(await _svc(session, operator).update_wo(wo_id, payload, version)))


@router.post("/work-orders/{wo_id}/transition", response_model=Resp[WorkOrderOut], summary="工单状态流转")
async def transition_wo(
    wo_id: int,
    target: WorkOrderStatus = Query(...),
    operator: str = Header("system", alias="X-Operator"),
    session: AsyncSession = Depends(get_db),
):
    wo = await _svc(session, operator).transition(wo_id, target)
    return Resp.ok(_wo(wo), message=f"工单已流转为 {target.value}")


@router.get("/work-orders/{wo_id}/operations", response_model=Resp[list[OperationStep]], summary="工序进度")
async def operations(wo_id: int, session: AsyncSession = Depends(get_db)):
    return Resp.ok(await _svc(session, "system").operations(wo_id))


@router.post("/work-orders/{wo_id}/report", response_model=Resp[ReportOut], summary="工序级报工")
async def report(
    wo_id: int,
    payload: ReportReq,
    operator: str = Header("system", alias="X-Operator"),
    session: AsyncSession = Depends(get_db),
):
    result = await _svc(session, operator).report(wo_id, payload)
    if result.duplicated:
        return Resp.ok(result, message="重复提交已忽略")
    if result.finished:
        return Resp.ok(result, message=f"工单完工，成品批次 {result.finished_batch} 已入库")
    return Resp.ok(result, message="报工成功")


@router.post("/work-orders/{wo_id}/scrap", response_model=Resp[WorkOrderOut], summary="报废登记")
async def scrap(
    wo_id: int,
    payload: ScrapReq,
    operator: str = Header("system", alias="X-Operator"),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_wo(await _svc(session, operator).scrap(wo_id, payload)), message="报废已登记")


@router.get("/progress", summary="报工流水")
async def progress(
    wo_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    session: AsyncSession = Depends(get_db),
):
    rows = await _svc(session, "system").list_progress(wo_id, limit)
    return Resp.ok(
        [
            {
                "id": r.id,
                "wo_id": r.wo_id,
                "seq": r.seq,
                "good_qty": str(r.good_qty),
                "bad_qty": str(r.bad_qty),
                "station": r.station,
                "operator": r.operator,
                "note": r.note,
                "logged_at": r.logged_at,
            }
            for r in rows
        ]
    )


@router.post("/inspections", response_model=Resp[InspectionOut], summary="登记检验记录")
async def create_inspection(
    payload: InspectionIn,
    operator: str = Header("system", alias="X-Operator"),
    session: AsyncSession = Depends(get_db),
):
    q = await _svc(session, operator).add_inspection(payload)
    return Resp.ok(
        InspectionOut(
            **payload.model_dump(exclude={"inspector"}),
            id=q.id,
            inspector=q.inspector,
            inspected_at=q.inspected_at,
        ),
        message="检验记录已登记",
    )


@router.get("/inspections", response_model=Resp[PageData[InspectionOut]], summary="检验记录分页列表")
async def list_inspection(
    wo_id: int | None = Query(None),
    product: str | None = Query(None),
    page: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await _svc(session, "system").list_inspection(wo_id, product, page)
    data = [
        InspectionOut(
            id=r.id,
            wo_id=r.wo_id,
            product_code=r.product_code,
            product_batch=r.product_batch,
            inspect_item=r.inspect_item,
            result=r.result,
            defect_code=r.defect_code,
            defect_desc=r.defect_desc,
            defect_images=r.defect_images or [],
            inspector=r.inspector,
            note=r.note,
            inspected_at=r.inspected_at,
        )
        for r in rows
    ]
    return Resp.page(data, total, page.page, page.size)


@router.get("/inspections/stats", summary="质量统计（合格率与缺陷 Top10）")
async def inspection_stats(session: AsyncSession = Depends(get_db)):
    return Resp.ok(await _svc(session, "system").quality_stats())


def _trace_out(r) -> TraceOut:
    return TraceOut(
        id=r.id,
        wo_id=r.wo_id,
        product_batch=r.product_batch,
        material_id=r.material_id,
        material_batch=r.material_batch,
        event_type=r.event_type,
        qty=r.qty,
        operator=r.operator,
        detail=r.detail or {},
        created_at=r.created_at,
    )


@router.get("/trace", response_model=Resp[list[TraceOut]], summary="追溯事件列表")
async def trace(
    wo_id: int | None = Query(None),
    limit: int = Query(200, le=1000),
    session: AsyncSession = Depends(get_db),
):
    rows = await _svc(session, "system").list_trace(wo_id, limit)
    return Resp.ok([_trace_out(r) for r in rows])


@router.get("/trace/forward/{product_batch}", summary="正向追溯：成品批次 → 用料与工单")
async def forward_trace(product_batch: str, session: AsyncSession = Depends(get_db)):
    rows = await _svc(session, "system").forward_trace(product_batch)
    return Resp.ok(
        {"product_batch": product_batch, "count": len(rows), "events": [_trace_out(r) for r in rows]}
    )


@router.get("/trace/backward/{material_batch}", summary="反向追溯：原料批次 → 流向的成品")
async def backward_trace(material_batch: str, session: AsyncSession = Depends(get_db)):
    rows = await _svc(session, "system").backward_trace(material_batch)
    return Resp.ok(
        {
            "material_batch": material_batch,
            "count": len(rows),
            "events": [_trace_out(r) for r in rows],
        }
    )


@router.get("/trace/tree/{product_batch}", summary="追溯树：成品批次 → 工单 → 全部事件")
async def trace_tree(product_batch: str, session: AsyncSession = Depends(get_db)):
    return Resp.ok(await _svc(session, "system").trace_tree(product_batch))
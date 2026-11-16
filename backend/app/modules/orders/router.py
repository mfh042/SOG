"""订单 REST 路由。"""
import csv
import io
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import OrderStatus
from app.core.deps import Pagination, get_db, get_pagination
from app.core.response import PageData, Resp
from app.modules.orders.schemas import (
    OrderCreate,
    OrderOut,
    OrderSplitIn,
    OrderUpdate,
    ReleaseOut,
)
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/api/orders", tags=["订单管理"])


def _to_out(o) -> OrderOut:
    data = OrderOut.model_validate(o, from_attributes=True)
    data.qty = sum((i.qty for i in o.items), type(o.items[0].qty if o.items else __import__("decimal").Decimal)())
    return data


@router.post("", response_model=Resp[OrderOut], summary="创建订单")
async def create_order(
    payload: OrderCreate,
    session: AsyncSession = Depends(get_db),
):
    order = await OrderService(session).create(payload)
    return Resp.ok(_to_out(order))


@router.get("", response_model=Resp[PageData[OrderOut]], summary="订单分页列表")
async def list_orders(
    status: str | None = Query(None, description="DRAFT/RELEASED/IN_PROGRESS/COMPLETED/CLOSED/CANCELLED"),
    customer: str | None = Query(None),
    page: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await OrderService(session).list(status, customer, page)
    return Resp.page([_to_out(r) for r in rows], total, page.page, page.size)


@router.get("/no/{order_no}", response_model=Resp[OrderOut], summary="按订单号查询")
async def get_order_by_no(order_no: str, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_to_out(await OrderService(session).get_by_no(order_no)))


@router.get("/{order_id}", response_model=Resp[OrderOut], summary="订单详情")
async def get_order(order_id: int, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_to_out(await OrderService(session).get(order_id)))


@router.put("/{order_id}", response_model=Resp[OrderOut], summary="编辑订单（含订单行整体替换）")
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    version: int = Query(..., description="乐观锁版本号"),
    session: AsyncSession = Depends(get_db),
):
    order = await OrderService(session).update(order_id, payload, version)
    return Resp.ok(_to_out(order))


@router.post("/{order_id}/transition", response_model=Resp[OrderOut], summary="订单状态流转")
async def transition(
    order_id: int,
    target: OrderStatus = Query(...),
    session: AsyncSession = Depends(get_db),
):
    order = await OrderService(session).transition(order_id, target)
    return Resp.ok(_to_out(order), message=f"已流转为 {target.value}")


@router.get("/{order_id}/work-orders", summary="订单关联工单（仅返回摘要）")
async def order_work_orders(order_id: int, session: AsyncSession = Depends(get_db)):
    rows = await OrderService(session).list_work_orders(order_id)
    return Resp.ok(
        [
            {
                "id": r.id,
                "wo_no": r.wo_no,
                "product_code": r.product_code,
                "product_name": r.product_name,
                "plan_qty": str(r.plan_qty),
                "status": r.status,
            }
            for r in rows
        ]
    )


@router.post("/{order_id}/release", response_model=Resp[ReleaseOut], summary="释放订单并生成工单")
async def release_order(order_id: int, session: AsyncSession = Depends(get_db)):
    result = await OrderService(session).release(order_id)
    message = "释放成功"
    if result.warnings:
        message = f"释放成功，但有 {len(result.warnings)} 项缺料"
    return Resp.ok(result, message=message)


@router.get("/{order_id}/kit-check", summary="订单齐套检查（BOM 驱动）")
async def order_kit_check(order_id: int, session: AsyncSession = Depends(get_db)):
    result = await OrderService(session).kit_check(order_id)
    return Resp.ok(result)


@router.post("/{order_id}/split", response_model=Resp[OrderOut], summary="订单拆分：拆出前 N 台为新订单")
async def split_order(
    order_id: int,
    payload: OrderSplitIn,
    session: AsyncSession = Depends(get_db),
):
    new_order = await OrderService(session).split(order_id, payload.split_qty)
    return Resp.ok(_to_out(new_order), message=f"已拆出新订单 {new_order.order_no}")


@router.post("/{order_id}/reschedule", response_model=Resp[OrderOut], summary="订单排产：更新计划日期")
async def reschedule_order(
    order_id: int,
    planned_date: str = Query(..., description="YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db),
):
    order = await OrderService(session).reschedule(order_id, planned_date)
    return Resp.ok(_to_out(order), message="计划日期已更新")


@router.post("/{order_id}/adjust-qty", response_model=Resp[OrderOut], summary="订单调整：更新订单行数量")
async def adjust_qty_order(
    order_id: int,
    qty: float = Query(..., gt=0),
    session: AsyncSession = Depends(get_db),
):
    order = await OrderService(session).adjust_qty(order_id, qty)
    return Resp.ok(_to_out(order), message="数量已更新")


@router.post("/batch-release", summary="批量下达：将多个草稿订单释放生成工单")
async def batch_release(
    order_ids: list[int],
    session: AsyncSession = Depends(get_db),
):
    result = await OrderService(session).batch_release(order_ids)
    return Resp.ok(result)


@router.post("/import", summary="CSV 批量导入生产工单")
async def import_orders(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gbk")
    rows = list(csv.DictReader(io.StringIO(text)))
    result = await OrderService(session).import_orders(rows)
    return Resp.ok(result, message=f"导入完成：{result['created']} 成功，{result['failed']} 失败")
"""订单 REST 路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import OrderStatus
from app.core.deps import Pagination, get_db, get_pagination
from app.core.response import PageData, Resp
from app.modules.orders.schemas import (
    OrderCreate,
    OrderOut,
    OrderUpdate,
    ReleaseOut,
)
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/api/orders", tags=["订单管理"])


def _to_out(o) -> OrderOut:
    return OrderOut.model_validate(o, from_attributes=True)


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
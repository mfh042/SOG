"""SOP 作业指导 REST 路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.response import Resp
from app.modules.sop.schemas import SopCreate, SopOut, SopUpdate
from app.modules.sop.service import SopService

router = APIRouter(prefix="/api/sops", tags=["SOP 作业指导"])


def _to_out(s) -> SopOut:
    return SopOut.model_validate(s, from_attributes=True)


@router.post("", response_model=Resp[SopOut], summary="创建/发布 SOP")
async def create_sop(payload: SopCreate, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_to_out(await SopService(session).create(payload)), message="SOP 已创建")


@router.get("", response_model=Resp[list[SopOut]], summary="SOP 列表（按产品/关键词过滤）")
async def list_sops(
    product_code: str | None = Query(None),
    keyword: str | None = Query(None),
    active_only: bool = Query(True),
    session: AsyncSession = Depends(get_db),
):
    if product_code:
        rows = await SopService(session).list_by_product(product_code, active_only)
    else:
        rows = await SopService(session).list_all(keyword, active_only)
    return Resp.ok([_to_out(r) for r in rows])


@router.get("/{sop_id}", response_model=Resp[SopOut], summary="SOP 详情")
async def get_sop(sop_id: int, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_to_out(await SopService(session).get(sop_id)))


@router.get("/for-operation/{product_code}/{operation_seq}", response_model=Resp[SopOut], summary="产品工序 SOP 查询")
async def get_for_op(
    product_code: str,
    operation_seq: int,
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await SopService(session).get_for_operation(product_code, operation_seq)))


@router.put("/{sop_id}", response_model=Resp[SopOut], summary="更新 SOP")
async def update_sop(
    sop_id: int,
    payload: SopUpdate,
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await SopService(session).update(sop_id, payload)), message="SOP 已更新")


@router.delete("/{sop_id}", summary="停用 SOP")
async def delete_sop(sop_id: int, session: AsyncSession = Depends(get_db)):
    await SopService(session).delete(sop_id)
    return Resp.ok(message="已停用")

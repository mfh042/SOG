"""不良代码 REST 路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.response import Resp
from app.modules.quality.schemas import DefectCodeCreate, DefectCodeOut, DefectCodeUpdate
from app.modules.quality.service import QualityService

router = APIRouter(prefix="/api/defect-codes", tags=["不良代码字典"])


def _to_out(d) -> DefectCodeOut:
    return DefectCodeOut.model_validate(d, from_attributes=True)


@router.post("", response_model=Resp[DefectCodeOut], summary="创建不良代码")
async def create_defect(payload: DefectCodeCreate, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_to_out(await QualityService(session).create(payload)), message="不良代码已创建")


@router.get("", response_model=Resp[list[DefectCodeOut]], summary="不良代码列表")
async def list_defects(
    category: str | None = Query(None),
    severity: str | None = Query(None),
    active_only: bool = Query(True),
    session: AsyncSession = Depends(get_db),
):
    rows = await QualityService(session).list(category, severity, active_only)
    return Resp.ok([_to_out(r) for r in rows])


@router.get("/{code}", response_model=Resp[DefectCodeOut], summary="按代码查询不良详情")
async def get_defect(code: str, session: AsyncSession = Depends(get_db)):
    return Resp.ok(_to_out(await QualityService(session).get_by_code(code)))


@router.put("/{code_id}", response_model=Resp[DefectCodeOut], summary="更新不良代码")
async def update_defect(
    code_id: int,
    payload: DefectCodeUpdate,
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await QualityService(session).update(code_id, payload)), message="已更新")


@router.delete("/{code_id}", response_model=Resp[DefectCodeOut], summary="停用不良代码")
async def delete_defect(code_id: int, session: AsyncSession = Depends(get_db)):
    await QualityService(session).delete(code_id)
    return Resp.ok(message="已停用")

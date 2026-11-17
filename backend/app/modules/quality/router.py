"""不良代码 + 检验类型 REST 路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db
from app.core.permissions import require_perm
from app.core.response import Resp
from app.modules.quality.schemas import (
    DefectCodeCreate, DefectCodeOut, DefectCodeUpdate,
    InspectTypeCreate, InspectTypeOut, InspectTypeUpdate,
)
from app.modules.quality.service import QualityService

router = APIRouter(prefix="/api", tags=["质量字典"])


def _to_defect(d) -> DefectCodeOut:
    return DefectCodeOut.model_validate(d, from_attributes=True)


def _to_inspect(t) -> InspectTypeOut:
    return InspectTypeOut.model_validate(t, from_attributes=True)


# ============ 不良代码 ============

@router.post("/defect-codes", response_model=Resp[DefectCodeOut], summary="创建不良代码")
async def create_defect(
    payload: DefectCodeCreate,
    user: dict = Depends(get_current_user),
    _: dict = Depends(require_perm("defect:create")),
    session: AsyncSession = Depends(get_db),
):
    d = await QualityService(session).create_defect(payload)
    await log_audit(session, "DEFECT_CREATE", "defect_code", d.id, {"code": d.code, "category": d.category}, user=user)
    await session.commit()
    return Resp.ok(_to_defect(d), message="不良代码已创建")


@router.get("/defect-codes", response_model=Resp[list[DefectCodeOut]], summary="不良代码列表")
async def list_defects(
    category: str | None = Query(None),
    severity: str | None = Query(None),
    active_only: bool = Query(True),
    _: dict = Depends(require_perm("defect:read")),
    session: AsyncSession = Depends(get_db),
):
    rows = await QualityService(session).list_defects(category, severity, active_only)
    return Resp.ok([_to_defect(r) for r in rows])


@router.get("/defect-codes/{code}", response_model=Resp[DefectCodeOut], summary="按代码查询不良详情")
async def get_defect(
    code: str,
    _: dict = Depends(require_perm("defect:read")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_defect(await QualityService(session).get_defect_by_code(code)))


@router.put("/defect-codes/{code_id}", response_model=Resp[DefectCodeOut], summary="更新不良代码")
async def update_defect(
    code_id: int,
    payload: DefectCodeUpdate,
    user: dict = Depends(get_current_user),
    _: dict = Depends(require_perm("defect:update")),
    session: AsyncSession = Depends(get_db),
):
    d = await QualityService(session).update_defect(code_id, payload)
    await log_audit(session, "DEFECT_UPDATE", "defect_code", d.id, payload.model_dump(exclude_unset=True), user=user)
    await session.commit()
    return Resp.ok(_to_defect(d), message="已更新")


@router.delete("/defect-codes/{code_id}", summary="停用不良代码")
async def delete_defect(
    code_id: int,
    user: dict = Depends(get_current_user),
    _: dict = Depends(require_perm("defect:update")),
    session: AsyncSession = Depends(get_db),
):
    await QualityService(session).delete_defect(code_id)
    await log_audit(session, "DEFECT_DELETE", "defect_code", code_id, user=user)
    await session.commit()
    return Resp.ok(message="已停用")


# ============ 检验类型 ============

@router.post("/inspect-types", response_model=Resp[InspectTypeOut], summary="新建检验类型")
async def create_inspect_type(
    payload: InspectTypeCreate,
    user: dict = Depends(get_current_user),
    _: dict = Depends(require_perm("quality:create")),
    session: AsyncSession = Depends(get_db),
):
    t = await QualityService(session).create_inspect_type(payload)
    await log_audit(session, "INSPECT_TYPE_CREATE", "inspect_type", t.id, payload.model_dump(), user=user)
    await session.commit()
    return Resp.ok(_to_inspect(t), message="检验类型已创建")


@router.get("/inspect-types", response_model=Resp[list[InspectTypeOut]], summary="检验类型列表")
async def list_inspect_types(
    category: str | None = Query(None),
    active_only: bool = Query(True),
    _: dict = Depends(require_perm("quality:read")),
    session: AsyncSession = Depends(get_db),
):
    rows = await QualityService(session).list_inspect_types(category, active_only)
    return Resp.ok([_to_inspect(r) for r in rows])


@router.get("/inspect-types/{code}", response_model=Resp[InspectTypeOut], summary="按代码查询检验类型")
async def get_inspect_type(
    code: str,
    _: dict = Depends(require_perm("quality:read")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_inspect(await QualityService(session).get_inspect_type_by_code(code)))


@router.put("/inspect-types/{type_id}", response_model=Resp[InspectTypeOut], summary="更新检验类型")
async def update_inspect_type(
    type_id: int,
    payload: InspectTypeUpdate,
    user: dict = Depends(get_current_user),
    _: dict = Depends(require_perm("quality:update")),
    session: AsyncSession = Depends(get_db),
):
    t = await QualityService(session).update_inspect_type(type_id, payload)
    await log_audit(session, "INSPECT_TYPE_UPDATE", "inspect_type", t.id, payload.model_dump(exclude_unset=True), user=user)
    await session.commit()
    return Resp.ok(_to_inspect(t), message="已更新")


@router.delete("/inspect-types/{type_id}", summary="停用检验类型")
async def delete_inspect_type(
    type_id: int,
    user: dict = Depends(get_current_user),
    _: dict = Depends(require_perm("quality:update")),
    session: AsyncSession = Depends(get_db),
):
    await QualityService(session).delete_inspect_type(type_id)
    await log_audit(session, "INSPECT_TYPE_DELETE", "inspect_type", type_id, user=user)
    await session.commit()
    return Resp.ok(message="已停用")
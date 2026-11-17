"""审计日志 REST 路由 — ADMIN 权限专属。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_perm
from app.core.response import Resp
from app.core.audit import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["审计日志"])


@router.get("", summary="审计日志列表（支持多条件过滤 + 时间范围）")
async def list_logs(
    action: str | None = Query(None),
    target_type: str | None = Query(None),
    actor_username: str | None = Query(None),
    result: str | None = Query(None),
    from_time: datetime | None = Query(None),
    to_time: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_perm("admin:audit")),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if actor_username:
        stmt = stmt.where(AuditLog.actor_username == actor_username)
    if result:
        stmt = stmt.where(AuditLog.result == result)
    if from_time:
        stmt = stmt.where(AuditLog.created_at >= from_time)
    if to_time:
        stmt = stmt.where(AuditLog.created_at <= to_time)

    total_stmt = select(AuditLog)
    for cond in stmt.whereclause.clauses if stmt.whereclause else []:
        total_stmt = total_stmt.where(cond)

    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(AuditLog)
    if stmt.whereclause:
        count_stmt = count_stmt.where(*stmt.whereclause.clauses)
    total = (await session.execute(count_stmt)).scalar_one()

    rows = list(
        (await session.execute(stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset))).scalars().all()
    )
    data = [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "actor_username": r.actor_username,
            "actor_role": r.actor_role,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "detail": r.detail,
            "result": r.result,
            "ip": r.ip,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return Resp.ok({"total": int(total), "items": data, "limit": limit, "offset": offset})


@router.get("/actions", summary="所有审计动作类型（供前端筛选）")
async def list_actions(
    _: dict = Depends(require_perm("admin:audit")),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog.action).distinct().order_by(AuditLog.action)
    rows = (await session.execute(stmt)).scalars().all()
    return Resp.ok(sorted(rows))
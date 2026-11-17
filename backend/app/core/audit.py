"""审计日志核心模块 — 记录关键操作 + 权限变更。"""
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy import JSON, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column()
    actor_username: Mapped[str | None] = mapped_column(String(64))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[str | None] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(String(16), default="SUCCESS")
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)


def _sanitize(obj: Any) -> Any:
    """把不可 JSON 序列化的对象转成可序列化。"""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if k not in ("password", "token", "secret")}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return _sanitize(obj.model_dump())
    if hasattr(obj, "__dict__") and not isinstance(obj, (str, int, float, bool)):
        return _sanitize(vars(obj))
    return obj


async def log_audit(
    session: AsyncSession,
    action: str,
    target_type: str,
    target_id: str | None = None,
    detail: dict | None = None,
    result: str = "SUCCESS",
    user: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    actor_id = int(user["user_id"]) if user and "user_id" in user else None
    actor_username = user.get("username") if user else None
    actor_role = user.get("role") if user else None
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None

    log = AuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=_sanitize(detail or {}),
        result=result,
        ip=ip,
        user_agent=ua,
    )
    session.add(log)
    return log
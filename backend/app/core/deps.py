"""公共依赖：会话、分页参数、当前操作人（认证预留）、JWT 鉴权。"""
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.exceptions import UnauthorizedException


@dataclass
class Pagination:
    page: int = 1
    size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def get_pagination(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=200, description="每页条数"),
) -> Pagination:
    return Pagination(page=page, size=size)


def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


def get_operator(request: Request) -> str:
    """当前操作人。

    预留：接入统一认证后从 JWT / 会话解析；当前从 X-Operator 头取，默认 system。
    """
    return request.headers.get("X-Operator", "system")


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """JWT 鉴权依赖：从 Authorization: Bearer <token> 解析当前用户。

    解析成功返回 {"user_id": int, "role": str, "username": str, "display_name": str}。
    未携带 token 或 token 无效抛 UnauthorizedException。
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise UnauthorizedException("缺少 Bearer Token")
    token = auth[7:]

    from app.modules.auth.crypto import decode_access_token
    from app.modules.auth.repository import UserRepository

    payload = decode_access_token(
        token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    if not payload:
        raise UnauthorizedException("Token 无效或已过期")

    user_id = int(payload["sub"])
    u = await UserRepository(session).get(user_id)
    if not u or not u.is_active:
        raise UnauthorizedException("用户不存在或已停用")

    return {
        "user_id": u.id,
        "role": u.role,
        "username": u.username,
        "display_name": u.display_name,
    }
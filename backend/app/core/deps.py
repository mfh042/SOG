"""公共依赖：会话、分页参数、当前操作人（认证预留）。"""
from dataclasses import dataclass

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session


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

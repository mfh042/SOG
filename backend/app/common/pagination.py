"""分页查询工具：count + 切片，供 Repository 复用。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination


async def count_total(session: AsyncSession, stmt) -> int:
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    return int(total or 0)

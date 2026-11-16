"""不良代码仓储。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.models import DefectCode


class QualityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, d: DefectCode) -> DefectCode:
        self.session.add(d)
        await self.session.flush()
        return d

    async def get(self, code_id: int) -> DefectCode | None:
        return await self.session.get(DefectCode, code_id)

    async def get_by_code(self, code: str) -> DefectCode | None:
        return await self.session.scalar(select(DefectCode).where(DefectCode.code == code))

    async def list_all(
        self,
        category: str | None = None,
        severity: str | None = None,
        active_only: bool = True,
    ) -> list[DefectCode]:
        stmt = select(DefectCode)
        if category:
            stmt = stmt.where(DefectCode.category == category)
        if severity:
            stmt = stmt.where(DefectCode.severity == severity)
        if active_only:
            stmt = stmt.where(DefectCode.is_active.is_(True))
        return list((await self.session.scalars(stmt.order_by(DefectCode.code))).all())

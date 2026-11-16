"""不良代码业务。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.quality.models import DefectCode
from app.modules.quality.repository import QualityRepository
from app.modules.quality.schemas import DefectCodeCreate, DefectCodeUpdate


class QualityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = QualityRepository(session)

    async def create(self, payload: DefectCodeCreate) -> DefectCode:
        existing = await self.repo.get_by_code(payload.code)
        if existing:
            raise ConflictException(f"不良代码 {payload.code} 已存在")
        d = DefectCode(**payload.model_dump())
        result = await self.repo.add(d)
        await self.session.commit()
        return result

    async def update(self, code_id: int, payload: DefectCodeUpdate) -> DefectCode:
        d = await self.repo.get(code_id)
        if not d:
            raise NotFoundException("不良代码不存在")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(d, k, v)
        await self.session.commit()
        return d

    async def delete(self, code_id: int) -> None:
        d = await self.repo.get(code_id)
        if not d:
            raise NotFoundException("不良代码不存在")
        d.is_active = False
        await self.session.commit()

    async def list(self, category: str | None, severity: str | None, active_only: bool = True):
        return await self.repo.list_all(category, severity, active_only)

    async def get_by_code(self, code: str) -> DefectCode:
        d = await self.repo.get_by_code(code)
        if not d:
            raise NotFoundException(f"不良代码 {code} 不存在")
        return d

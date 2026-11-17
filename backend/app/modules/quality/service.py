"""不良代码 & 检验类型业务。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.quality.models import DefectCode, InspectType
from app.modules.quality.schemas import (
    DefectCodeCreate, DefectCodeUpdate,
    InspectTypeCreate, InspectTypeUpdate,
)


class QualityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- DefectCode ----------
    async def create_defect(self, payload: DefectCodeCreate) -> DefectCode:
        existing = await self.session.scalar(
            select(DefectCode).where(DefectCode.code == payload.code)
        )
        if existing:
            raise ConflictException(f"不良代码 {payload.code} 已存在")
        d = DefectCode(**payload.model_dump())
        self.session.add(d)
        await self.session.commit()
        await self.session.refresh(d)
        return d

    async def update_defect(self, code_id: int, payload: DefectCodeUpdate) -> DefectCode:
        d = await self.session.get(DefectCode, code_id)
        if not d:
            raise NotFoundException("不良代码不存在")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(d, k, v)
        await self.session.commit()
        await self.session.refresh(d)
        return d

    async def delete_defect(self, code_id: int) -> None:
        d = await self.session.get(DefectCode, code_id)
        if not d:
            raise NotFoundException("不良代码不存在")
        d.is_active = False
        await self.session.commit()

    async def list_defects(self, category: str | None, severity: str | None, active_only: bool = True):
        stmt = select(DefectCode)
        if active_only:
            stmt = stmt.where(DefectCode.is_active.is_(True))
        if category:
            stmt = stmt.where(DefectCode.category == category)
        if severity:
            stmt = stmt.where(DefectCode.severity == severity)
        return list((await self.session.scalars(stmt.order_by(DefectCode.code))).all())

    async def get_defect_by_code(self, code: str) -> DefectCode:
        d = await self.session.scalar(select(DefectCode).where(DefectCode.code == code))
        if not d:
            raise NotFoundException(f"不良代码 {code} 不存在")
        return d

    # ---------- InspectType ----------
    async def create_inspect_type(self, payload: InspectTypeCreate) -> InspectType:
        existing = await self.session.scalar(
            select(InspectType).where(InspectType.code == payload.code)
        )
        if existing:
            raise ConflictException(f"检验类型 {payload.code} 已存在")
        t = InspectType(**payload.model_dump())
        self.session.add(t)
        await self.session.commit()
        await self.session.refresh(t)
        return t

    async def update_inspect_type(self, type_id: int, payload: InspectTypeUpdate) -> InspectType:
        t = await self.session.get(InspectType, type_id)
        if not t:
            raise NotFoundException("检验类型不存在")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(t, k, v)
        await self.session.commit()
        await self.session.refresh(t)
        return t

    async def delete_inspect_type(self, type_id: int) -> None:
        t = await self.session.get(InspectType, type_id)
        if not t:
            raise NotFoundException("检验类型不存在")
        t.is_active = False
        await self.session.commit()

    async def list_inspect_types(self, category: str | None = None, active_only: bool = True):
        stmt = select(InspectType)
        if active_only:
            stmt = stmt.where(InspectType.is_active.is_(True))
        if category:
            stmt = stmt.where(InspectType.category == category)
        return list((await self.session.scalars(stmt.order_by(InspectType.code))).all())

    async def get_inspect_type_by_code(self, code: str) -> InspectType:
        t = await self.session.scalar(select(InspectType).where(InspectType.code == code))
        if not t:
            raise NotFoundException(f"检验类型 {code} 不存在")
        return t
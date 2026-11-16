"""SOP 业务。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.sop.models import Sop
from app.modules.sop.repository import SopRepository
from app.modules.sop.schemas import SopCreate, SopUpdate


class SopService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SopRepository(session)

    async def create(self, payload: SopCreate) -> Sop:
        existing = await self.repo.get_active_for_op(payload.product_code, payload.operation_seq)
        if existing:
            existing.is_active = False
            await self.session.flush()
        s = Sop(**payload.model_dump())
        result = await self.repo.add(s)
        await self.session.commit()
        return result

    async def update(self, sop_id: int, payload: SopUpdate) -> Sop:
        s = await self.repo.get(sop_id)
        if not s:
            raise NotFoundException("SOP 不存在")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(s, k, v)
        await self.session.commit()
        return s

    async def delete(self, sop_id: int) -> None:
        s = await self.repo.get(sop_id)
        if not s:
            raise NotFoundException("SOP 不存在")
        s.is_active = False
        await self.session.commit()

    async def get(self, sop_id: int) -> Sop:
        s = await self.repo.get(sop_id)
        if not s:
            raise NotFoundException("SOP 不存在")
        return s

    async def get_for_operation(self, product_code: str, operation_seq: int) -> Sop:
        s = await self.repo.get_active_for_op(product_code, operation_seq)
        if not s:
            raise NotFoundException(f"产品 {product_code} 工序 {operation_seq} 无 SOP")
        return s

    async def list_by_product(self, product_code: str, active_only: bool = True):
        return await self.repo.list_by_product(product_code, active_only)

    async def list_all(self, keyword: str | None = None, active_only: bool = True):
        return await self.repo.list_all(keyword, active_only)

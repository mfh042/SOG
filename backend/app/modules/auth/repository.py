"""用户仓储。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AppUser


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, u: AppUser) -> AppUser:
        self.session.add(u)
        await self.session.flush()
        return u

    async def get(self, user_id: int) -> AppUser | None:
        return await self.session.get(AppUser, user_id)

    async def get_by_username(self, username: str) -> AppUser | None:
        stmt = select(AppUser).where(AppUser.username == username)
        return await self.session.scalar(stmt)

    async def list_all(self) -> list[AppUser]:
        return list(
            (await self.session.scalars(select(AppUser).order_by(AppUser.id))).all()
        )

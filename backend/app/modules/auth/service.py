"""认证业务：注册、登录、Token 签发。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.modules.auth.crypto import create_access_token, hash_password, verify_password
from app.modules.auth.models import AppUser
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)

    async def register(self, payload: RegisterIn) -> AppUser:
        existing = await self.repo.get_by_username(payload.username)
        if existing:
            raise ConflictException("用户名已被占用")
        u = AppUser(
            username=payload.username,
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
            station_code=payload.station_code,
        )
        result = await self.repo.add(u)
        await self.session.commit()
        return result

    async def login(self, payload: LoginIn) -> TokenOut:
        u = await self.repo.get_by_username(payload.username)
        if not u or not u.is_active:
            raise UnauthorizedException("用户名或密码错误")
        if not verify_password(payload.password, u.password_hash):
            raise UnauthorizedException("用户名或密码错误")
        token = create_access_token(
            sub=str(u.id),
            role=u.role,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_access_expire_minutes,
        )
        return TokenOut(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_access_expire_minutes * 60,
        )

    async def get_user(self, user_id: int) -> AppUser:
        u = await self.repo.get(user_id)
        if not u or not u.is_active:
            raise UnauthorizedException("用户不存在或已停用")
        return u

    async def list_users(self):
        return await self.repo.list_all()
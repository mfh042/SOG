"""JWT 鉴权 REST 路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.response import Resp
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/api/auth", tags=["JWT 鉴权"])


def _user_out(u) -> UserOut:
    return UserOut.model_validate(u, from_attributes=True)


@router.post("/register", response_model=Resp[UserOut], summary="注册用户")
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_db)):
    u = await AuthService(session).register(payload)
    return Resp.ok(_user_out(u), message="注册成功")


@router.post("/login", response_model=Resp[TokenOut], summary="登录（返回 JWT）")
async def login(payload: LoginIn, session: AsyncSession = Depends(get_db)):
    token = await AuthService(session).login(payload)
    return Resp.ok(token, message="登录成功")


@router.get("/users", response_model=Resp[list[UserOut]], summary="用户列表")
async def list_users(session: AsyncSession = Depends(get_db)):
    rows = await AuthService(session).list_users()
    return Resp.ok([_user_out(r) for r in rows])

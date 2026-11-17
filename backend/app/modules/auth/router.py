"""JWT 鉴权 REST 路由 + 用户管理 + 角色权限。"""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.permissions import (
    ALL_PERMISSIONS,
    ROLE_NAMES,
    catalog,
    invalidate_role,
    load_role_perms,
    role_list_async,
    require_perm,
)
from app.core.response import Resp
from app.modules.auth.models import RolePermission
from app.modules.auth.schemas import (
    LoginIn,
    RegisterIn,
    RolePermUpdate,
    TokenOut,
    UserOut,
    UserUpdate,
)
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
async def list_users(
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    rows = await AuthService(session).list_users()
    return Resp.ok([_user_out(r) for r in rows])


@router.put("/users/{user_id}", response_model=Resp[UserOut], summary="更新用户")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    u = await AuthService(session).update_user(user_id, payload)
    return Resp.ok(_user_out(u), message="用户已更新")


@router.delete("/users/{user_id}", response_model=Resp, summary="停用用户")
async def delete_user(
    user_id: int,
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    await AuthService(session).delete_user(user_id)
    return Resp.ok(message="用户已停用")


@router.get("/me", response_model=Resp[UserOut], summary="当前登录用户信息")
async def me(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    u = await AuthService(session).get_user(user["user_id"])
    return Resp.ok(_user_out(u))


@router.get("/roles", response_model=Resp[list[dict]], summary="角色权限列表（含持久化）")
async def roles(
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    data = await role_list_async(session)
    return Resp.ok(data)


@router.get("/permissions/catalog", response_model=Resp[list[str]], summary="可选权限清单")
async def permissions_catalog(
    _: dict = Depends(require_perm("material:read")),
):
    return Resp.ok(catalog())


@router.get("/permissions/roles", response_model=Resp[dict], summary="角色名称映射")
async def permission_role_names(
    _: dict = Depends(require_perm("material:read")),
):
    return Resp.ok(ROLE_NAMES)


@router.put("/roles/{role}/permissions", response_model=Resp[list[str]], summary="保存角色权限")
async def save_role_permissions(
    role: str,
    payload: RolePermUpdate,
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    if role == "ADMIN":
        return Resp.ok(["*"], message="ADMIN 永远拥有全部权限")
    if role not in ROLE_NAMES:
        from app.core.exceptions import ConflictException
        raise ConflictException(f"未知角色: {role}")

    await session.execute(delete(RolePermission).where(RolePermission.role == role))
    cleaned = sorted({p for p in payload.permissions if p and p != "*"})
    for p in cleaned:
        session.add(RolePermission(role=role, permission=p))
    await session.commit()
    invalidate_role(role)
    return Resp.ok(cleaned, message="权限已保存")

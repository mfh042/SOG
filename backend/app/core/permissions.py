"""RBAC 权限守卫：角色-权限映射 + FastAPI 依赖。

角色体系 5 级：
- ADMIN     系统管理员（全部权限）
- MANAGER   生产主管
- PLANNER   计划员
- QUALITY   质量专员
- OPERATOR  操作工（最小权限）

持久化：role_permission 表存实际值，启动时从硬编码种子初始化（仅当表为空）。
ADMIN 特殊处理：永远拥有所有权限 (* 通配)，不读表。
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.exceptions import ForbiddenException

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ADMIN": {"*"},
    "MANAGER": {
        "material:read", "material:create", "material:update", "material:delete",
        "bom:read", "bom:create", "bom:update", "bom:delete",
        "orders:read", "orders:create", "orders:release", "orders:update", "orders:cancel",
        "production:read", "production:report", "production:transition",
        "quality:read", "quality:create", "quality:update",
        "defect:read", "defect:create", "defect:update",
        "sop:read", "sop:create", "sop:update", "sop:delete", "sop:upload",
        "dashboard:read",
        "trace:read",
        "inventory:all", "inventory:read", "inventory:write",
        "wip:read",
        "device:read",
        "admin:audit",
    },
    "PLANNER": {
        "orders:read", "orders:create", "orders:release",
        "bom:read", "bom:create", "bom:update",
        "material:read", "material:create",
        "production:read", "production:report",
        "quality:read",
        "defect:read",
        "sop:read", "sop:create", "sop:update", "sop:upload",
        "dashboard:read",
        "trace:read",
        "inventory:read",
    },
    "QUALITY": {
        "production:read",
        "quality:read", "quality:create", "quality:update",
        "defect:read", "defect:create", "defect:update",
        "sop:read",
        "trace:read",
        "dashboard:read",
    },
    "OPERATOR": {
        "production:read", "production:report",
        "sop:read",
        "trace:read",
        "wip:read",
        "inventory:read",
        "dashboard:read",
    },
}

ALL_PERMISSIONS: list[str] = sorted({
    p for perms in ROLE_PERMISSIONS.values() for p in perms if p != "*"
})

ROLE_NAMES: dict[str, str] = {
    "ADMIN": "系统管理员",
    "MANAGER": "生产主管",
    "PLANNER": "计划员",
    "QUALITY": "质量专员",
    "OPERATOR": "操作工",
}

_db_cache: dict[str, set[str]] = {}


def invalidate_role(role: str) -> None:
    _db_cache.pop(role, None)


async def load_role_perms(session, role: str) -> set[str]:
    if role in _db_cache:
        return _db_cache[role]
    from sqlalchemy import select
    from app.modules.auth.models import RolePermission
    rows = (await session.execute(
        select(RolePermission.permission).where(RolePermission.role == role)
    )).scalars().all()
    perms = set(rows)
    if not perms and role in ROLE_PERMISSIONS:
        perms = {p for p in ROLE_PERMISSIONS[role] if p != "*"}
    _db_cache[role] = perms
    return perms


async def _has_perm_async(session, role: str, perm: str) -> bool:
    if role == "ADMIN":
        return True
    perms = await load_role_perms(session, role)
    return "*" in perms or perm in perms


def _has_perm(role: str, perm: str) -> bool:
    """同步 fallback（无 session 场景，仅查硬编码 + 缓存）。"""
    if role == "ADMIN":
        return True
    if role in _db_cache:
        perms = _db_cache[role]
        return "*" in perms or perm in perms
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or perm in perms


def require_perm(perm: str):
    async def _check(
        user: Annotated[dict, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> dict:
        role = user["role"]
        if not await _has_perm_async(session, role, perm):
            raise ForbiddenException(f"角色 {role} 无权执行 {perm}")
        return user
    return _check


def require_role(*roles: str):
    async def _check(
        user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if user["role"] not in roles:
            raise ForbiddenException(f"需要角色 {roles}，当前为 {user['role']}")
        return user
    return _check


def role_can(role: str, perm: str) -> bool:
    return _has_perm(role, perm)


async def role_list_async(session) -> list[dict]:
    result = []
    for role in ROLE_PERMISSIONS:
        if role == "ADMIN":
            result.append({
                "role": role,
                "role_name": ROLE_NAMES.get(role, role),
                "permissions": ["*"],
                "note": "系统管理员拥有全部权限，不可编辑",
            })
        else:
            perms = await load_role_perms(session, role)
            result.append({
                "role": role,
                "role_name": ROLE_NAMES.get(role, role),
                "permissions": sorted(perms),
                "note": None,
            })
    return result


def role_list() -> list[dict]:
    return [
        {"role": r, "role_name": ROLE_NAMES.get(r, r), "permissions": sorted(p)}
        for r, p in ROLE_PERMISSIONS.items()
    ]


def catalog() -> list[str]:
    return ALL_PERMISSIONS


def role_names() -> dict[str, str]:
    return ROLE_NAMES.copy()
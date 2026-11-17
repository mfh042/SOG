"""用户（JWT 鉴权）模型 + 角色权限持久化。"""
from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin


class AppUser(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="OPERATOR", index=True)
    station_code: Mapped[str | None] = mapped_column(String(32), index=True, comment="绑定工位")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RolePermission(Base):
    __tablename__ = "role_permission"
    __table_args__ = (UniqueConstraint("role", "permission", name="uq_role_perm"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    permission: Mapped[str] = mapped_column(String(128), index=True)
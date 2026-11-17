"""质量字典：检验类型 + 不良代码。"""
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin


class InspectType(Base, TimestampMixin):
    __tablename__ = "inspect_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32), default="FQC", index=True)
    sample_strategy: Mapped[str] = mapped_column(String(32), default="FIXED")
    sample_count: Mapped[int] = mapped_column(Integer, default=5)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DefectCode(Base, TimestampMixin):
    __tablename__ = "defect_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), default="OTHER", index=True)
    severity: Mapped[str] = mapped_column(String(16), default="MINOR", index=True)
    disposal_guide: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
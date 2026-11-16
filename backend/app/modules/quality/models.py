"""质量字典：不良代码。"""
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin


class DefectCode(Base, TimestampMixin):
    __tablename__ = "defect_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), default="OTHER", index=True)
    severity: Mapped[str] = mapped_column(String(16), default="MINOR", index=True)
    disposal_guide: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

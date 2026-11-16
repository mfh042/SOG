"""SOP 作业指导模型。"""
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin


class Sop(Base, TimestampMixin):
    __tablename__ = "sop"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(String(64), index=True)
    operation_seq: Mapped[int] = mapped_column()
    operation_name: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str | None] = mapped_column(Text)
    content_url: Mapped[str | None] = mapped_column(String(512))
    version: Mapped[str] = mapped_column(String(16), default="V1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

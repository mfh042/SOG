"""SOP 作业指导模型。"""
from sqlalchemy import Boolean, String, Text, JSON
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
    media_type: Mapped[str | None] = mapped_column(String(32), comment="image / pdf / video")
    media_url: Mapped[str | None] = mapped_column(String(512))
    annotations: Mapped[dict | None] = mapped_column(JSON, comment="标注数据 JSON")
    version: Mapped[str] = mapped_column(String(16), default="V1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SopTemplate(Base, TimestampMixin):
    __tablename__ = "sop_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default="通用", comment="类别：CNC/装配/检验/通用/...")
    description: Mapped[str | None] = mapped_column(String(512))
    title_template: Mapped[str] = mapped_column(String(256), comment="标题模板，{product} {operation} 等占位符")
    operation_name_default: Mapped[str | None] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text, comment="模板正文，支持占位符 {product} {operation_seq}")
    content_url: Mapped[str | None] = mapped_column(String(512))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, comment="系统内置不可删")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
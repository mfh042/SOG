"""BOM 物料清单模型。"""
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base, TimestampMixin


class Bom(Base, TimestampMixin):
    __tablename__ = "bom"
    __table_args__ = (
        UniqueConstraint("product_material_id", "version", name="uq_bom_product_version"),
        Index("ix_bom_product", "product_material_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_material_id: Mapped[int] = mapped_column(
        ForeignKey("material.id", ondelete="CASCADE"), index=True, comment="产品物料 ID"
    )
    version: Mapped[str] = mapped_column(String(32), default="V1", comment="BOM 版本")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="当前生效版本")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    remark: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["BomItem"]] = relationship(back_populates="bom", cascade="all, delete-orphan")


class BomItem(Base):
    __tablename__ = "bom_item"
    __table_args__ = (
        UniqueConstraint("bom_id", "component_material_id", name="uq_bom_item_component"),
        Index("ix_bom_item_bom", "bom_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bom_id: Mapped[int] = mapped_column(ForeignKey("bom.id", ondelete="CASCADE"), index=True)
    component_material_id: Mapped[int] = mapped_column(
        ForeignKey("material.id", ondelete="RESTRICT"), index=True
    )
    qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), CheckConstraint("qty > 0"), comment="单套用量"
    )
    loss_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), CheckConstraint("loss_rate >= 0"), default=0, comment="损耗率"
    )
    seq: Mapped[int] = mapped_column(default=1, comment="顺序号")

    bom: Mapped[Bom] = relationship(back_populates="items")
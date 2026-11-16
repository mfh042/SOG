"""订单管理模型：销售/生产订单头 + 订单行。"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base, TimestampMixin, VersionMixin
from app.common.enums import OrderStatus


class SalesOrder(Base, TimestampMixin, VersionMixin):
    __tablename__ = "sales_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="订单号")
    customer_name: Mapped[str] = mapped_column(String(128), index=True, comment="客户")
    product_model: Mapped[str] = mapped_column(String(128), comment="产品型号")
    priority: Mapped[int] = mapped_column(default=3, comment="优先级 1高~5低")
    status: Mapped[str] = mapped_column(String(16), default=OrderStatus.DRAFT.value, index=True)
    planned_date: Mapped[date | None] = mapped_column(Date, comment="计划交付日期")
    note: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_item"
    __table_args__ = (UniqueConstraint("order_id", "line_no", name="uq_order_line"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sales_order.id", ondelete="CASCADE"), index=True)
    line_no: Mapped[int] = mapped_column(default=1, comment="行号")
    material_code: Mapped[str] = mapped_column(String(64), index=True, comment="物料编码")
    material_name: Mapped[str] = mapped_column(String(128), comment="物料名称")
    spec: Mapped[str | None] = mapped_column(String(256), comment="规格")
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), comment="需求数量")
    unit: Mapped[str] = mapped_column(String(16), default="PCS")

    order: Mapped[SalesOrder] = relationship(back_populates="items")

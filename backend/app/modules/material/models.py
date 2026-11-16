"""物料管控模型：物料主数据、库存台账、出入库流水。"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin
from app.common.enums import MaterialType, StockStatus


class Material(Base, TimestampMixin):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="物料编码")
    name: Mapped[str] = mapped_column(String(128), index=True, comment="物料名称")
    type: Mapped[str] = mapped_column(String(16), index=True, comment="RAW/WIP/FINISHED")
    spec: Mapped[str | None] = mapped_column(String(256), comment="规格型号")
    unit: Mapped[str] = mapped_column(String(16), default="PCS")
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0, comment="安全库存")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    attrs: Mapped[dict] = mapped_column(JSON, default=dict, comment="扩展属性 JSONB")


class Inventory(Base, TimestampMixin):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("material_id", "batch_no", "location", name="uq_inv_batch_loc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("material.id", ondelete="RESTRICT"), index=True
    )
    batch_no: Mapped[str] = mapped_column(String(64), index=True, comment="批次号")
    location: Mapped[str] = mapped_column(String(64), default="WH-01", comment="库位")
    qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0, comment="在手数量")
    qty_reserved: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0, comment="已预留数量")
    status: Mapped[str] = mapped_column(String(16), default=StockStatus.AVAILABLE.value)

    @property
    def available(self) -> Decimal:
        return self.qty_on_hand - self.qty_reserved


class StockTransaction(Base):
    __tablename__ = "stock_transaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"), index=True)
    batch_no: Mapped[str] = mapped_column(String(64), index=True)
    txn_type: Mapped[str] = mapped_column(String(16), comment="IN/RESERVE/RELEASE/OUT/SCRAP")
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 3))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 3), comment="结存")
    ref_type: Mapped[str | None] = mapped_column(String(32), comment="来源单据类型")
    ref_id: Mapped[int | None] = mapped_column(index=True, comment="来源单据 ID")
    operator: Mapped[str] = mapped_column(String(64), default="system")
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

"""生产管理模型：工单、报工进度、质量检验、批次追溯链。"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin, VersionMixin
from app.common.enums import WorkOrderStatus


class WorkOrder(Base, TimestampMixin, VersionMixin):
    __tablename__ = "work_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    wo_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sales_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales_order.id", ondelete="SET NULL"), index=True
    )
    product_code: Mapped[str] = mapped_column(String(64), index=True, comment="产品编码")
    product_name: Mapped[str] = mapped_column(String(128))
    plan_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), comment="计划数量")
    done_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0, comment="完工数量")
    scrap_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0, comment="报废数量")
    status: Mapped[str] = mapped_column(
        String(16), default=WorkOrderStatus.PLANNED.value, index=True
    )
    line: Mapped[str | None] = mapped_column(String(32), comment="产线")
    station: Mapped[str | None] = mapped_column(String(32), comment="工位")
    route: Mapped[list] = mapped_column(JSONB, default=list, comment="工艺路线/工位序列")
    planned_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductionProgress(Base):
    __tablename__ = "production_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    wo_id: Mapped[int] = mapped_column(ForeignKey("work_order.id"), index=True)
    seq: Mapped[int | None] = mapped_column(default=None, comment="工序序号")
    good_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), comment="本次合格数量")
    bad_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0, comment="本次不良数量")
    station: Mapped[str | None] = mapped_column(String(32))
    operator: Mapped[str] = mapped_column(String(64), default="system")
    note: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), index=True, comment="幂等键：同键重复提交仅生效一次"
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class QualityInspection(Base):
    __tablename__ = "quality_inspection"

    id: Mapped[int] = mapped_column(primary_key=True)
    wo_id: Mapped[int | None] = mapped_column(ForeignKey("work_order.id"), index=True)
    product_code: Mapped[str | None] = mapped_column(String(64), index=True)
    product_batch: Mapped[str | None] = mapped_column(String(64), index=True, comment="成品批次")
    inspect_item: Mapped[str] = mapped_column(String(128), comment="检验项目")
    inspect_type: Mapped[str] = mapped_column(String(32), default="FQC", index=True, comment="IQC/IPQC/PQC/FQC/OQC/SPQC")
    operation_seq: Mapped[int | None] = mapped_column(Integer, index=True, comment="对应工序序号")
    sample_qty: Mapped[int] = mapped_column(Integer, default=1)
    result: Mapped[str] = mapped_column(String(16), index=True, comment="PASS/FAIL/REWORK")
    defect_code: Mapped[str | None] = mapped_column(String(32), index=True, comment="不良代码")
    defect_desc: Mapped[str | None] = mapped_column(Text, comment="缺陷描述/处置指引")
    defect_images: Mapped[list] = mapped_column(JSONB, default=list, comment="不良图册/图片")
    inspector: Mapped[str] = mapped_column(String(64), default="system")
    judge: Mapped[str | None] = mapped_column(String(64), comment="判定人")
    note: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class TraceRecord(Base):
    """批次追溯链：正向(订单→工单→成品/物料批次)、反向(物料批次→工单→成品)。"""
    __tablename__ = "trace_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    wo_id: Mapped[int | None] = mapped_column(ForeignKey("work_order.id"), index=True)
    product_batch: Mapped[str | None] = mapped_column(String(64), index=True, comment="成品批次")
    material_id: Mapped[int | None] = mapped_column(ForeignKey("material.id"), index=True)
    material_batch: Mapped[str | None] = mapped_column(String(64), index=True, comment="物料批次")
    event_type: Mapped[str] = mapped_column(String(24), index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=0)
    operator: Mapped[str] = mapped_column(String(64), default="system")
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
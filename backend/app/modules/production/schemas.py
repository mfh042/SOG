"""生产 / 质量 / 追溯请求响应模型。"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class WorkOrderCreate(BaseModel):
    sales_order_id: int | None = None
    product_code: str
    product_name: str
    plan_qty: Decimal = Field(gt=0)
    line: str | None = None
    station: str | None = None
    route: list[dict[str, Any]] = []
    planned_start: datetime | None = None
    planned_end: datetime | None = None


class WorkOrderUpdate(BaseModel):
    product_name: str | None = None
    plan_qty: Decimal | None = Field(None, gt=0)
    line: str | None = None
    station: str | None = None
    route: list[dict[str, Any]] | None = None
    planned_start: datetime | None = None
    planned_end: datetime | None = None


class WorkOrderOut(BaseModel):
    id: int
    wo_no: str
    sales_order_id: int | None
    product_code: str
    product_name: str
    plan_qty: Decimal
    done_qty: Decimal
    scrap_qty: Decimal
    status: str
    line: str | None
    station: str | None
    route: list[dict[str, Any]]
    version: int


class MaterialUse(BaseModel):
    material_id: int
    qty: Decimal = Field(gt=0)
    batch_no: str | None = Field(None, description="原料批次；为空时按 FIFO 自动选批")
    location: str | None = None


class ReportReq(BaseModel):
    good_qty: Decimal = Field(ge=0)
    bad_qty: Decimal = Field(0, ge=0)
    station: str | None = None
    note: str | None = None
    seq: int | None = Field(None, description="工序序号；为空则按当前进行中的工序")
    product_batch: str | None = Field(None, description="成品批次；为空时末道自动生成 FG-{工单号}-{日期}")
    idempotency_key: str | None = Field(None, max_length=64, description="幂等键，重复提交仅生效一次")
    materials: list[MaterialUse] = Field(
        default_factory=list, description="本次消耗的原料；填则同步出库并写入正向追溯链"
    )


class ReportOut(BaseModel):
    work_order: WorkOrderOut
    duplicated: bool = False
    finished: bool = False
    finished_qty: Decimal = Decimal(0)
    finished_batch: str | None = None


class ScrapReq(BaseModel):
    qty: Decimal = Field(gt=0)
    note: str | None = None
    seq: int | None = None


class OperationStep(BaseModel):
    seq: int
    name: str
    station: str | None = None
    status: str = "pending"
    good_qty: Decimal = 0
    bad_qty: Decimal = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class InspectionIn(BaseModel):
    wo_id: int | None = None
    product_code: str | None = None
    product_batch: str | None = None
    inspect_item: str
    result: str = Field(description="PASS/FAIL/REWORK")
    defect_code: str | None = None
    defect_desc: str | None = None
    defect_images: list[str] = []
    inspector: str | None = None
    note: str | None = None


class InspectionOut(InspectionIn):
    id: int
    inspected_at: datetime


class TraceOut(BaseModel):
    id: int
    wo_id: int | None
    wo_no: str | None = None
    product_batch: str | None
    material_id: int | None
    material_batch: str | None
    event_type: str
    qty: Decimal
    operator: str
    detail: dict[str, Any]
    created_at: datetime
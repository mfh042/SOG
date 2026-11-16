"""订单请求 / 响应模型。"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    line_no: int = Field(1, ge=1)
    material_code: str
    material_name: str
    spec: str | None = None
    qty: Decimal = Field(gt=0)
    unit: str = "PCS"


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=128)
    product_model: str = Field(min_length=1, max_length=128)
    priority: int = Field(3, ge=1, le=5)
    planned_date: date | None = None
    note: str | None = None
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemUpdate(BaseModel):
    line_no: int | None = Field(None, ge=1)
    material_code: str | None = None
    material_name: str | None = None
    spec: str | None = None
    qty: Decimal | None = Field(None, gt=0)
    unit: str | None = None


class OrderUpdate(BaseModel):
    customer_name: str | None = None
    product_model: str | None = None
    priority: int | None = Field(None, ge=1, le=5)
    planned_date: date | None = None
    note: str | None = None
    items: list[OrderItemIn] | None = Field(None, min_length=1, description="传则整体替换订单行")


class OrderItemOut(OrderItemIn):
    id: int


class OrderOut(BaseModel):
    id: int
    order_no: str
    customer_name: str
    product_model: str
    priority: int
    status: str
    planned_date: date | None
    note: str | None
    version: int
    items: list[OrderItemOut]


class ShortageOut(BaseModel):
    material_code: str
    material_name: str
    required: Decimal
    available: Decimal
    shortage: Decimal


class WorkOrderDraftOut(BaseModel):
    wo_no: str
    product_code: str
    product_name: str
    plan_qty: Decimal
    id: int | None = None


class ReleaseOut(BaseModel):
    order_no: str
    status: str
    version: int
    work_orders: list[WorkOrderDraftOut]
    warnings: list[ShortageOut]
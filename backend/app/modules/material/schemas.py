"""物料 / 库存 / 流水请求响应模型。"""
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MaterialIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(description="RAW/WIP/FINISHED")
    spec: str | None = None
    unit: str = "PCS"
    safety_stock: Decimal = Field(0, ge=0)
    attrs: dict[str, Any] = {}


class MaterialOut(MaterialIn):
    id: int
    status: str


class MaterialUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    type: str | None = None
    spec: str | None = None
    unit: str | None = None
    safety_stock: Decimal | None = Field(None, ge=0)
    attrs: dict[str, Any] | None = None


class StockIn(BaseModel):
    material_id: int
    batch_no: str = Field(min_length=1)
    location: str = "WH-01"
    qty: Decimal = Field(gt=0)
    remark: str | None = None


class StockOpReq(BaseModel):
    material_id: int
    batch_no: str | None = None
    location: str | None = None
    qty: Decimal = Field(gt=0)
    ref_type: str | None = None
    ref_id: int | None = None
    remark: str | None = None


class StockAdjust(BaseModel):
    inventory_id: int
    physical_qty: Decimal = Field(ge=0)
    reason: str = Field(min_length=1, max_length=64, description="SURPLUS/SHORT/DAMAGE/OTHER")
    remark: str | None = None


class InventoryOut(BaseModel):
    id: int
    material_id: int
    batch_no: str
    location: str
    qty_on_hand: Decimal
    qty_reserved: Decimal
    available: Decimal
    status: str


class TxnOut(BaseModel):
    id: int
    material_id: int
    batch_no: str
    txn_type: str
    qty: Decimal
    balance_after: Decimal
    ref_type: str | None
    ref_id: int | None
    operator: str
    remark: str | None
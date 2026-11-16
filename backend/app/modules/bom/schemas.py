from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BomItemIn(BaseModel):
    component_material_id: int
    qty: float = Field(gt=0)
    loss_rate: float = Field(ge=0, default=0)
    seq: int = Field(ge=1, default=1)


class BomItemOut(BaseModel):
    id: int
    bom_id: int
    component_material_id: int
    component_code: str | None = None
    component_name: str | None = None
    qty: float
    loss_rate: float
    seq: int

    model_config = {"from_attributes": True}


class BomCreate(BaseModel):
    product_material_id: int
    version: str = "V1"
    remark: str | None = None
    is_active: bool = True
    items: list[BomItemIn] = Field(min_length=1)


class BomUpdate(BaseModel):
    version: str | None = None
    remark: str | None = None
    items: list[BomItemIn] | None = None


class BomOut(BaseModel):
    id: int
    product_material_id: int
    product_code: str | None = None
    product_name: str | None = None
    version: str
    is_active: bool
    status: str
    remark: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[BomItemOut] = []

    model_config = {"from_attributes": True}


class BomListOut(BaseModel):
    id: int
    product_material_id: int
    product_code: str | None = None
    product_name: str | None = None
    version: str
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    model_config = {"from_attributes": True}


class BomActivateOut(BaseModel):
    bom: BomOut
    deactivated_id: int | None = None


class ShortageItem(BaseModel):
    component_material_id: int
    component_code: str
    component_name: str
    need_qty: float
    available_qty: float
    shortage_qty: float


class ShortageOut(BaseModel):
    product_code: str
    product_name: str
    order_qty: float
    ok: bool
    items: list[ShortageItem]
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RemoteCustomer(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str
    code: str = ""
    name: str
    contact: str = ""
    phone: str = ""
    address: str = ""


class RemoteMaterial(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str
    code: str
    name: str
    type: str = "RAW"
    spec: str = ""
    unit: str = "PCS"


class RemoteOrderItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str = ""
    line_no: int = 1
    material_code: str
    material_name: str = ""
    spec: str = ""
    qty: float
    unit: str = "PCS"


class RemoteOrder(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str
    order_no: str
    customer_name: str
    product_model: str = ""
    priority: int = 3
    planned_date: str = ""
    note: str = ""
    items: list[RemoteOrderItem] = Field(default_factory=list)


class RemoteBomItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str = ""
    component_code: str
    component_name: str = ""
    qty: float
    loss_rate: float = 0
    seq: int = 1


class RemoteBom(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str
    product_code: str
    version: str = "V1"
    is_active: bool = True
    items: list[RemoteBomItem] = Field(default_factory=list)


class RemoteInventory(BaseModel):
    model_config = ConfigDict(extra="allow")
    external_id: str = ""
    material_code: str
    batch_no: str = ""
    location: str = ""
    qty_on_hand: float = 0
    qty_reserved: float = 0


class ExternalSystemAdapter(ABC):
    system_name: str = "BASE"

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]: ...

    async def fetch_orders(self, since: str | None = None) -> list[RemoteOrder]:
        return []

    async def fetch_materials(self, since: str | None = None) -> list[RemoteMaterial]:
        return []

    async def fetch_boms(self, since: str | None = None) -> list[RemoteBom]:
        return []

    async def fetch_inventory(self, since: str | None = None) -> list[RemoteInventory]:
        return []

    async def fetch_customers(self, since: str | None = None) -> list[RemoteCustomer]:
        return []
"""不良代码 & 检验类型 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


class DefectCodeBase(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)
    category: str = "OTHER"
    severity: str = "MINOR"
    disposal_guide: str | None = None


class DefectCodeCreate(DefectCodeBase):
    pass


class DefectCodeUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    severity: str | None = None
    disposal_guide: str | None = None
    is_active: bool | None = None


class DefectCodeOut(DefectCodeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InspectTypeBase(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=64)
    category: str = "FQC"
    sample_strategy: str = "FIXED"
    sample_count: int = 5
    description: str | None = None


class InspectTypeCreate(InspectTypeBase):
    pass


class InspectTypeUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    sample_strategy: str | None = None
    sample_count: int | None = None
    description: str | None = None
    is_active: bool | None = None


class InspectTypeOut(InspectTypeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
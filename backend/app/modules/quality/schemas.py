"""不良代码请求响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


class DefectCodeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    category: str = Field("OTHER", max_length=32)
    severity: str = Field("MINOR", pattern="^(CRITICAL|MAJOR|MINOR|SUGGESTION)$")
    disposal_guide: str | None = None


class DefectCodeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    category: str | None = Field(None, max_length=32)
    severity: str | None = Field(None, pattern="^(CRITICAL|MAJOR|MINOR|SUGGESTION)$")
    disposal_guide: str | None = None
    is_active: bool | None = None


class DefectCodeOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    severity: str
    disposal_guide: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

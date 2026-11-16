"""SOP 请求响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


class SopCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    operation_seq: int = Field(ge=1)
    operation_name: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    content: str | None = None
    content_url: str | None = Field(None, max_length=512)
    version: str = Field("V1", max_length=16)


class SopUpdate(BaseModel):
    operation_name: str | None = Field(None, min_length=1, max_length=64)
    title: str | None = Field(None, min_length=1, max_length=256)
    content: str | None = None
    content_url: str | None = Field(None, max_length=512)
    version: str | None = Field(None, max_length=16)
    is_active: bool | None = None


class SopOut(BaseModel):
    id: int
    product_code: str
    operation_seq: int
    operation_name: str
    title: str
    content: str | None = None
    content_url: str | None = None
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

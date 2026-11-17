"""SOP 请求响应模型。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SopCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    operation_seq: int = Field(ge=1)
    operation_name: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    content: str | None = None
    content_url: str | None = Field(None, max_length=512)
    media_type: str | None = Field(None, max_length=32)
    media_url: str | None = Field(None, max_length=512)
    annotations: dict | None = None
    version: str = Field("V1", max_length=16)


class SopUpdate(BaseModel):
    operation_name: str | None = Field(None, min_length=1, max_length=64)
    title: str | None = Field(None, min_length=1, max_length=256)
    content: str | None = None
    content_url: str | None = Field(None, max_length=512)
    media_type: str | None = Field(None, max_length=32)
    media_url: str | None = Field(None, max_length=512)
    annotations: dict | None = None
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
    media_type: str | None = None
    media_url: str | None = None
    annotations: dict | None = None
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    category: str = Field("通用", max_length=32)
    description: str | None = Field(None, max_length=512)
    title_template: str = Field(min_length=1, max_length=256)
    operation_name_default: str | None = Field(None, max_length=64)
    content: str
    content_url: str | None = Field(None, max_length=512)


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    category: str | None = Field(None, max_length=32)
    description: str | None = Field(None, max_length=512)
    title_template: str | None = Field(None, min_length=1, max_length=256)
    operation_name_default: str | None = Field(None, max_length=64)
    content: str | None = None
    content_url: str | None = Field(None, max_length=512)
    is_active: bool | None = None


class TemplateOut(BaseModel):
    id: int
    name: str
    category: str
    description: str | None = None
    title_template: str
    operation_name_default: str | None = None
    content: str
    content_url: str | None = None
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateApplyIn(BaseModel):
    product_code: str
    operation_seq: int
    operation_name: str | None = None
    version: str = "V1"
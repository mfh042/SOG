"""认证请求响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field("OPERATOR", pattern="^(ADMIN|MANAGER|PLANNER|OPERATOR|QUALITY)$")
    station_code: str | None = Field(None, max_length=32)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    station_code: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
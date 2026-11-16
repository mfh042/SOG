"""统一响应包装。"""
from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageData(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int


class Resp(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None

    @staticmethod
    def ok(data: Any = None, message: str = "ok") -> "Resp[Any]":
        return Resp(code=0, message=message, data=data)

    @staticmethod
    def page(items: Sequence[T], total: int, page: int, size: int) -> "Resp[PageData[T]]":
        return Resp[PageData[T]](
            data=PageData[T](items=list(items), total=total, page=page, size=size)
        )
"""业务异常与全局异常处理器。"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class BizException(Exception):
    """可预期业务异常，由 Service 抛出，HTTP 状态默认 400。"""

    def __init__(self, message: str, code: int = 400, status: int = 400):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(message)


class NotFoundException(BizException):
    def __init__(self, message: str = "记录不存在"):
        super().__init__(message, code=404, status=404)


class ConflictException(BizException):
    """并发冲突：版本号不一致 / 库存不足 / 状态非法流转。"""

    def __init__(self, message: str = "状态冲突或数据已变更，请刷新重试"):
        super().__init__(message, code=409, status=409)


class UnauthorizedException(BizException):
    """鉴权失败：Token 无效 / 过期 / 无权限。"""

    def __init__(self, message: str = "未登录或身份已失效"):
        super().__init__(message, code=401, status=401)


class ForbiddenException(BizException):
    """权限不足。"""

    def __init__(self, message: str = "无权执行该操作"):
        super().__init__(message, code=403, status=403)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizException)
    async def _biz(_: Request, exc: BizException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"系统内部错误: {exc}", "data": None},
        )
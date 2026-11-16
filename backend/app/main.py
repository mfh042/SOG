"""SOG 后端入口。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8000
高并发部署：gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app
"""
import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.concurrency import shutdown_threadpool
from app.core.exceptions import register_exception_handlers
from app.core.response import Resp
from app.modules.material.router import router as material_router
from app.modules.orders.router import router as order_router
from app.modules.production.router import router as production_router

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动：可在此预热连接池、加载缓存、注册定时任务
    yield
    # 关闭：释放线程池与连接
    shutdown_threadpool()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(order_router)
app.include_router(material_router)
app.include_router(production_router)


@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    return Resp.ok({"status": "up", "env": settings.app_env})
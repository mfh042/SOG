"""SOG 后端入口。

启动：uvicorn app.main:app --loop selector --host 0.0.0.0 --port 8000
高并发部署：gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.common.base import Base
from app.core.config import settings
from app.core.concurrency import shutdown_threadpool
from app.core.db import AsyncSessionLocal, engine
from app.core.exceptions import register_exception_handlers
from app.core.response import Resp
from app.modules.auth.crypto import hash_password
from app.modules.auth.models import AppUser
from app.modules.auth.router import router as auth_router
from app.modules.bom.router import router as bom_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.material.models import Material
from app.modules.material.router import router as material_router
from app.modules.orders.models import OrderItem, SalesOrder
from app.modules.orders.router import router as order_router
from app.modules.production.router import router as production_router
from app.modules.quality.router import router as quality_router
from app.modules.sop.router import router as sop_router

logger = logging.getLogger("sog")


async def _init_db():
    """自动建表 + 种子数据（幂等，可反复执行）。"""
    import app.modules.auth.models  # noqa: F401  让 Base.metadata 注册
    import app.modules.bom.models  # noqa: F401
    import app.modules.material.models  # noqa: F401
    import app.modules.orders.models  # noqa: F401
    import app.modules.production.models  # noqa: F401
    import app.modules.quality.models  # noqa: F401
    import app.modules.sop.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ 数据库表已就绪")

    async with AsyncSessionLocal() as session:
        result = await session.scalar(select(AppUser).limit(1))
        if result is None:
            _seed_users(session)
            _seed_materials(session)
            await session.commit()
            logger.info("✓ 种子数据已写入")


def _seed_users(session):
    users = [
        ("admin",    "Admin",    "admin123",   "ADMIN"),
        ("planner",  "Planner",  "planner123", "PLANNER"),
        ("operator", "Operator", "op123",      "OPERATOR"),
        ("quality",  "Quality",  "qc123",      "QUALITY"),
    ]
    for username, display, pwd, role in users:
        session.add(
            AppUser(
                username=username,
                display_name=display,
                password_hash=hash_password(pwd),
                role=role,
                is_active=True,
            )
        )


def _seed_materials(session):
    materials = [
        ("GB-100", "减速机 GB-100",   "台", "FINISHED"),
        ("GB-200", "减速机 GB-200",   "台", "FINISHED"),
        ("M-001",  "电机总成 A 型",    "个", "WIP"),
        ("M-002",  "齿轮箱外壳",       "件", "WIP"),
        ("R-001",  "轴承 6205-2RS",    "个", "RAW"),
        ("R-002",  "O 型密封圈 Ø45",   "个", "RAW"),
    ]
    for code, name, unit, type_ in materials:
        session.add(
            Material(
                code=code,
                name=name,
                spec="",
                unit=unit,
                type=type_,
            )
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _init_db()
    yield
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

app.include_router(auth_router)
app.include_router(bom_router)
app.include_router(dashboard_router)
app.include_router(quality_router)
app.include_router(order_router)
app.include_router(material_router)
app.include_router(production_router)
app.include_router(sop_router)


@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    return Resp.ok({"status": "up", "env": settings.app_env})
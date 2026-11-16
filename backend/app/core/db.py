"""数据库引擎与会话管理（SQLAlchemy 2.0 async + psycopg3）。

高并发要点：
- 异步连接池替代逐请求新建连接；pool_size / max_overflow 由配置控制；
- 会话按请求注入（deps.get_db），用完即归还连接；
- 写事务在 Service 层显式 begin / commit / rollback，扣库存使用行级锁。
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """请求级会话依赖。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
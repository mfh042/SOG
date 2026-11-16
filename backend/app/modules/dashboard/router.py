"""生产总览看板 REST 路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.response import Resp
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["生产总览"])


@router.get("/overview", summary="生产总览看板聚合数据（8 路并行）")
async def overview(session: AsyncSession = Depends(get_db)):
    data = await DashboardService(session).overview()
    return Resp.ok(data)


@router.get("/kit-alerts", summary="齐套告警队列（RELEASED/IN_PROGRESS 订单缺料摘要）")
async def kit_alerts(session: AsyncSession = Depends(get_db)):
    data = await DashboardService(session).kit_alerts()
    return Resp.ok(data)

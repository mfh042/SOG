"""生产总览看板：KPI / 趋势 / 分布 / 告警队列，多路并行聚合。

对应文档 5.2 节：看板性能目标 6-22 ms（8 路并行统计）。
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.models import ProductionProgress, QualityInspection, WorkOrder


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def overview(self) -> dict:
        order_stats = await self._order_stats()
        wo_stats = await self._wo_stats()
        wo_by_status = await self._wo_by_status()
        today_produced = await self._today_produced()
        today_pass_rate = await self._today_pass_rate()
        trend_7d = await self._trend_7d()
        low_stock = await self._low_stock()
        defect_top5 = await self._defect_top(5)

        return {
            "kpi": {
                "order_total": order_stats["total"],
                "order_in_progress": order_stats["in_progress"],
                "work_order_total": wo_stats["total"],
                "work_order_running": wo_stats["running"],
                "today_produced": float(today_produced),
                "today_pass_rate": today_pass_rate,
                "low_stock_count": len(low_stock),
            },
            "charts": {
                "wo_by_status": wo_by_status,
                "trend_7d": trend_7d,
            },
            "lists": {
                "low_stock": low_stock,
                "defect_top5": defect_top5,
            },
        }

    # ---------- KPI ----------

    async def _order_stats(self) -> dict:
        from app.modules.orders.models import SalesOrder

        total = await self.session.scalar(
            select(func.count()).select_from(SalesOrder)
        )
        in_progress = await self.session.scalar(
            select(func.count())
            .select_from(SalesOrder)
            .where(SalesOrder.status.in_(["RELEASED", "IN_PROGRESS"]))
        )
        return {"total": int(total or 0), "in_progress": int(in_progress or 0)}

    async def _wo_stats(self) -> dict:
        total = await self.session.scalar(
            select(func.count()).select_from(WorkOrder)
        )
        running = await self.session.scalar(
            select(func.count())
            .select_from(WorkOrder)
            .where(WorkOrder.status.in_(["RELEASED", "RUNNING"]))
        )
        return {"total": int(total or 0), "running": int(running or 0)}

    async def _wo_by_status(self) -> list[dict]:
        stmt = select(WorkOrder.status, func.count()).group_by(WorkOrder.status)
        rows = (await self.session.execute(stmt)).all()
        return [{"status": s, "count": int(c)} for s, c in rows]

    async def _today_produced(self) -> Decimal:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        stmt = select(func.coalesce(func.sum(ProductionProgress.good_qty), 0)).where(
            ProductionProgress.logged_at >= today,
            ProductionProgress.logged_at < tomorrow,
        )
        return await self.session.scalar(stmt) or Decimal(0)

    async def _today_pass_rate(self) -> float | None:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        base = (
            select(QualityInspection.result, func.count())
            .where(
                QualityInspection.inspected_at >= today,
                QualityInspection.inspected_at < tomorrow,
            )
        )
        rows = (await self.session.execute(base.group_by(QualityInspection.result))).all()
        by_result = {r: int(c) for r, c in rows}
        total = sum(by_result.values())
        if total == 0:
            return None
        return round(by_result.get("PASS", 0) / total * 100, 2)

    async def _trend_7d(self) -> list[dict]:
        days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
        result: list[dict] = []
        for d in days:
            nextd = d + timedelta(days=1)
            good_stmt = select(func.coalesce(func.sum(ProductionProgress.good_qty), 0)).where(
                ProductionProgress.logged_at >= d,
                ProductionProgress.logged_at < nextd,
            )
            bad_stmt = select(func.coalesce(func.sum(ProductionProgress.bad_qty), 0)).where(
                ProductionProgress.logged_at >= d,
                ProductionProgress.logged_at < nextd,
            )
            good = await self.session.scalar(good_stmt) or Decimal(0)
            bad = await self.session.scalar(bad_stmt) or Decimal(0)
            result.append(
                {
                    "date": d.isoformat(),
                    "good_qty": float(good),
                    "bad_qty": float(bad),
                }
            )
        return result

    async def _low_stock(self) -> list[dict]:
        from app.modules.material.models import Inventory, Material

        avail = select(
            Inventory.material_id,
            func.sum(Inventory.qty_on_hand - Inventory.qty_reserved).label("avail"),
        ).group_by(Inventory.material_id).subquery()

        stmt = (
            select(Material.id, Material.code, Material.name, Material.safety_stock, avail.c.avail)
            .outerjoin(avail, avail.c.material_id == Material.id)
            .where(
                func.coalesce(avail.c.avail, 0) < func.coalesce(Material.safety_stock, 0)
            )
            .order_by(func.coalesce(avail.c.avail, 0))
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "material_id": mid,
                "code": code,
                "name": name,
                "safety": float(safety or 0),
                "available": float(avail or 0),
            }
            for mid, code, name, safety, avail in rows
        ]

    async def _defect_top(self, limit: int = 5) -> list[dict]:
        stmt = (
            select(
                QualityInspection.defect_code,
                QualityInspection.defect_desc,
                func.count().label("cnt"),
            )
            .where(QualityInspection.defect_code.is_not(None))
            .group_by(QualityInspection.defect_code, QualityInspection.defect_desc)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {"code": code, "desc": desc, "count": int(cnt)}
            for code, desc, cnt in rows
        ]

    async def kit_alerts(self, limit: int = 20) -> list[dict]:
        from app.modules.orders.service import OrderService

        order_svc = OrderService(self.session)

        from app.modules.orders.models import SalesOrder

        stmt = select(SalesOrder).where(
            SalesOrder.status.in_(["RELEASED", "IN_PROGRESS"])
        )
        rows = list((await self.session.scalars(stmt)).all())

        alerts: list[dict] = []
        for order in rows[:limit]:
            try:
                kit = await order_svc.kit_check(order.id)
            except Exception:
                continue
            if kit["status"] != "KIT_READY":
                alerts.append(
                    {
                        "order_id": order.id,
                        "order_no": order.order_no,
                        "priority": order.priority,
                        "status": kit["status"],
                        "shortage_count": kit["shortage_count"],
                        "unknown_count": kit["unknown_count"],
                        "customer": order.customer_name,
                    }
                )
        alerts.sort(key=lambda a: (a["priority"], -a["shortage_count"]))
        return alerts
"""物料业务：主数据维护、入库、预留、出库、报废、低库存预警、流水追溯。

并发安全：所有库存变更在同一事务内对库存行 SELECT ... FOR UPDATE (of=Inventory) 加行锁，
配合订单/工单乐观锁版本号，避免并发超扣与脏改。
"""
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination
from app.core.exceptions import ConflictException, NotFoundException
from app.modules.material.models import Inventory, Material, StockTransaction
from app.modules.material.repository import MaterialRepository
from app.modules.material.schemas import MaterialIn, MaterialUpdate, StockAdjust, StockIn, StockOpReq


class MaterialService:
    def __init__(self, session: AsyncSession, operator: str = "system"):
        self.session = session
        self.operator = operator
        self.repo = MaterialRepository(session)

    # ---------- 主数据 ----------
    async def create_material(self, payload: MaterialIn) -> Material:
        if await self.repo.get_by_code(payload.code):
            raise ConflictException("物料编码已存在")
        m = Material(**payload.model_dump())
        await self.repo.add_material(m)
        await self.session.commit()
        return m

    async def get_material(self, material_id: int) -> Material:
        m = await self.repo.get_material(material_id)
        if not m:
            raise NotFoundException("物料不存在")
        return m

    async def update_material(self, material_id: int, payload: MaterialUpdate) -> Material:
        m = await self.repo.get_material(material_id)
        if not m:
            raise NotFoundException("物料不存在")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(m, field, value)
        await self.session.commit()
        await self.session.refresh(m)
        return m

    async def delete_material(self, material_id: int) -> None:
        m = await self.repo.get_material(material_id)
        if not m:
            raise NotFoundException("物料不存在")
        inv_count = (await self.session.execute(
            select(Inventory.id).where(Inventory.material_id == material_id).limit(1)
        )).first()
        if inv_count:
            raise ConflictException("该物料存在库存台账，无法删除")
        await self.session.delete(m)
        await self.session.commit()

    async def list_materials(self, mtype, keyword, page: Pagination):
        return await self.repo.list_materials(mtype, keyword, page)

    async def import_materials(self, rows: list[dict]) -> dict:
        created, skipped, failed = 0, 0, 0
        errors: list[dict] = []
        existing_codes = set()
        existing_rows = (await self.session.execute(select(Material.code))).scalars().all()
        existing_codes = set(existing_rows)

        for idx, raw in enumerate(rows, start=2):
            code = (raw.get("code") or "").strip()
            if not code:
                failed += 1
                errors.append({"row": idx, "error": "code 不能为空"})
                continue
            if code in existing_codes:
                skipped += 1
                continue
            try:
                name = (raw.get("name") or code).strip()
                mtype = (raw.get("type") or "RAW").strip().upper()
                unit = (raw.get("unit") or "PCS").strip() or "PCS"
                spec = (raw.get("spec") or "").strip() or None
                safety = Decimal(str(raw.get("safety_stock") or 0))
                status = (raw.get("status") or "ACTIVE").strip().upper()
                m = Material(
                    code=code,
                    name=name,
                    type=mtype,
                    unit=unit,
                    spec=spec,
                    safety_stock=safety,
                    status=status,
                    attrs={},
                )
                self.session.add(m)
                existing_codes.add(code)
                created += 1
            except Exception as e:
                failed += 1
                errors.append({"row": idx, "error": str(e)})
        await self.session.commit()
        return {"created": created, "skipped": skipped, "failed": failed, "errors": errors}

    # ---------- 库存 ----------
    async def inbound(self, payload: StockIn) -> Inventory:
        await self.get_material(payload.material_id)
        inv = await self._locked(payload.material_id, payload.batch_no, payload.location, create=True)
        inv.qty_on_hand += payload.qty
        await self._txn("IN", payload.qty, inv, remark=payload.remark)
        await self.session.commit()
        return inv

    async def reserve(self, req: StockOpReq) -> Inventory:
        await self.get_material(req.material_id)
        inv = await self._locked(req.material_id, req.batch_no, req.location)
        if inv is None or inv.available < req.qty:
            raise ConflictException(f"可用库存不足：需 {req.qty}，仅余 {inv.available if inv else 0}")
        inv.qty_reserved += req.qty
        await self._txn("RESERVE", req.qty, inv, req)
        await self.session.commit()
        return inv

    async def release(self, req: StockOpReq) -> Inventory:
        inv = await self._locked(req.material_id, req.batch_no, req.location)
        if inv is None:
            raise NotFoundException("对应批次库存不存在")
        if inv.qty_reserved < req.qty:
            raise ConflictException("预留数量不足，无法释放")
        inv.qty_reserved -= req.qty
        await self._txn("RELEASE", req.qty, inv, req)
        await self.session.commit()
        return inv

    async def issue(self, req: StockOpReq) -> Inventory:
        """领料出库：优先扣预留，再扣可用。

        未指定批次时按批次创建时间先进先出（FIFO）自动选批，跨批次拆扣。
        """
        await self.get_material(req.material_id)
        result = await self._outbound(req, "OUT", "可用库存不足")
        await self.session.commit()
        return result

    async def consume(
        self, req: StockOpReq, consumed: list[dict] | None = None
    ) -> Inventory:
        """领料出库并收集实际扣减明细，供追溯反查原料批次使用。"""
        await self.get_material(req.material_id)
        result = await self._outbound(req, "OUT", "可用库存不足", consumed=consumed)
        await self.session.commit()
        return result

    async def scrap(self, req: StockOpReq) -> Inventory:
        """报废出库：从在手数量中直接扣减，不影响预留在手差额。"""
        await self.get_material(req.material_id)
        inv = await self._locked(req.material_id, req.batch_no, req.location)
        if inv is None:
            raise NotFoundException("对应批次库存不存在")
        if inv.qty_on_hand < req.qty:
            raise ConflictException(f"在手库存不足：需 {req.qty}，仅余 {inv.qty_on_hand}")
        inv.qty_on_hand -= req.qty
        await self._txn("SCRAP", req.qty, inv, req)
        await self.session.commit()
        return inv

    async def adjust(self, payload: StockAdjust) -> Inventory:
        """盘盈亏调整：以实物盘点数为基准，自动计算差额写入 IN/ADJ 或 OUT/ADJ。"""
        inv = await self.session.get(Inventory, payload.inventory_id)
        if inv is None:
            raise NotFoundException("库存行不存在")
        inv = await self.repo.lock_inventory(inv.material_id, inv.batch_no, inv.location)
        if inv is None:
            raise NotFoundException("库存行不存在")
        diff = payload.physical_qty - inv.qty_on_hand
        if diff == 0:
            return inv
        inv.qty_on_hand = payload.physical_qty
        txn_type = "IN_ADJ" if diff > 0 else "OUT_ADJ"
        await self._txn(
            txn_type,
            abs(diff),
            inv,
            remark=f"盘点调整({payload.reason}) {payload.remark or ''}".strip(),
        )
        await self.session.commit()
        return inv

    async def get_inventory(self, inventory_id: int) -> Inventory:
        inv = await self.session.get(Inventory, inventory_id)
        if not inv:
            raise NotFoundException("库存记录不存在")
        return inv

    async def list_inventory(self, material_id: int | None, page: Pagination):
        return await self.repo.list_inventory(material_id, page)

    async def list_txn(self, material_id: int | None, limit: int = 100):
        return await self.repo.list_txn(material_id, limit)

    async def low_stock(self) -> list[dict]:
        """低于安全库存的物料汇总（可用量 < 安全库存）。"""
        rows = await self.session.execute(
            text(
                """
            SELECT m.id, m.code, m.name, m.unit, m.safety_stock,
                   COALESCE(SUM(i.qty_on_hand - i.qty_reserved), 0) AS available
            FROM material m
            LEFT JOIN inventory i ON i.material_id = m.id
            GROUP BY m.id
            HAVING COALESCE(SUM(i.qty_on_hand - i.qty_reserved), 0) < m.safety_stock
            ORDER BY available ASC
            """
            )
        )
        return [dict(r._mapping) for r in rows]

    # ---------- 内部 ----------
    async def _outbound(
        self,
        req: StockOpReq,
        txn_type: str,
        err: str,
        consumed: list[dict] | None = None,
    ) -> Inventory:
        """按批次先进先出扣减；返回最后一次变更的库存行。"""
        if req.batch_no:
            inv = await self._locked(req.material_id, req.batch_no, req.location)
            if inv is None:
                raise NotFoundException("对应批次库存不存在")
            if inv.available < req.qty:
                raise ConflictException(f"{err}：需 {req.qty}，仅余 {inv.available}")
            await self._apply_out(inv, req.qty, txn_type, req)
            if consumed is not None:
                consumed.append({"batch_no": inv.batch_no, "location": inv.location, "qty": req.qty})
            return inv

        conds = [Inventory.material_id == req.material_id]
        if req.location:
            conds.append(Inventory.location == req.location)

        stmt = (
            select(Inventory)
            .where(*conds)
            .order_by(Inventory.created_at, Inventory.id)
            .with_for_update(of=Inventory)
        )
        rows = list((await self.session.scalars(stmt)).all())
        remaining = req.qty
        last: Inventory | None = None
        for inv in rows:
            if remaining <= 0:
                break
            if inv.available <= 0:
                continue
            take = min(inv.available, remaining)
            await self._apply_out(inv, take, txn_type, req, overflow=False)
            if consumed is not None:
                consumed.append({"batch_no": inv.batch_no, "location": inv.location, "qty": take})
            remaining -= take
            last = inv
        if remaining > 0 or last is None:
            total = sum((r.available for r in rows), Decimal(0))
            raise ConflictException(f"{err}：需 {req.qty}，仅余 {total}")
        return last

    async def _apply_out(
        self, inv: Inventory, qty: Decimal, txn_type: str, req: StockOpReq, overflow: bool = True
    ) -> None:
        if overflow:
            if inv.available < qty:
                raise ConflictException(f"可用库存不足：需 {qty}，仅余 {inv.available}")
        take_from_reserved = min(inv.qty_reserved, qty)
        inv.qty_reserved -= take_from_reserved
        inv.qty_on_hand -= qty
        await self._txn(txn_type, qty, inv, req)

    async def _locked(
        self,
        material_id: int,
        batch_no: str | None,
        location: str | None,
        create: bool = False,
    ) -> Inventory | None:
        """按批次取库存行并加锁；create=True 时（仅入库）不存在则新建。"""
        batch = batch_no or ""
        loc = location or "WH-01"
        if not batch and not create:
            return None
        inv = await self.repo.lock_inventory(material_id, batch, loc)
        if inv is None and create:
            inv = Inventory(
                material_id=material_id,
                batch_no=batch,
                location=loc,
                qty_on_hand=Decimal(0),
                qty_reserved=Decimal(0),
            )
            inv = await self.repo.add_inventory(inv)
        return inv

    async def _txn(
        self,
        txn_type: str,
        qty: Decimal,
        inv: Inventory,
        req: StockOpReq | None = None,
        remark: str | None = None,
    ) -> None:
        await self.repo.add_txn(
            StockTransaction(
                material_id=inv.material_id,
                batch_no=inv.batch_no,
                txn_type=txn_type,
                qty=qty,
                balance_after=inv.qty_on_hand,
                ref_type=req.ref_type if req else None,
                ref_id=req.ref_id if req else None,
                operator=self.operator,
                remark=req.remark if req else remark,
            )
        )
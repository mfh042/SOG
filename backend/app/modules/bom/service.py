from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.bom.models import Bom, BomItem
from app.modules.bom.repository import BomRepository
from app.modules.bom.schemas import (
    BomCreate,
    BomUpdate,
    BomOut,
    BomListOut,
    BomActivateOut,
    BomItemOut,
    ShortageItem,
    ShortageOut,
)
from app.modules.material.repository import MaterialRepository


class BomService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BomRepository(session)
        self.material_repo = MaterialRepository(session)

    async def create(self, payload: BomCreate) -> BomOut:
        product = await self.material_repo.get_material(payload.product_material_id)
        if product is None:
            raise NotFoundException("产品物料不存在")

        existing = await self.repo.get_by_product(payload.product_material_id, version=payload.version)
        if existing:
            raise ConflictException(f"BOM 版本 {payload.version} 已存在")

        if payload.is_active:
            await self.repo.ensure_only_one_active(payload.product_material_id)

        bom = Bom(
            product_material_id=payload.product_material_id,
            version=payload.version,
            is_active=payload.is_active,
            remark=payload.remark,
        )
        for item in payload.items:
            bom.items.append(
                BomItem(
                    component_material_id=item.component_material_id,
                    qty=item.qty,
                    loss_rate=item.loss_rate,
                    seq=item.seq,
                )
            )
        await self.repo.add(bom)
        await self.session.commit()
        bom = await self.repo.enrich_with_material_info(bom)
        return self._to_out(bom)

    async def get(self, bom_id: int) -> BomOut:
        bom = await self.repo.get(bom_id)
        if bom is None:
            raise NotFoundException("BOM 不存在")
        bom = await self.repo.enrich_with_material_info(bom)
        return self._to_out(bom)

    async def list(self, product_material_id: int | None = None, keyword: str | None = None) -> list[BomListOut]:
        boms = await self.repo.list_boms(product_material_id, keyword)
        result: list[BomListOut] = []
        for b in boms:
            count = await self.repo.count_items(b.id)
            bom = await self.repo.enrich_with_material_info(b)
            out = BomListOut.model_validate(bom, from_attributes=True)
            out.item_count = count
            result.append(out)
        return result

    async def update(self, bom_id: int, payload: BomUpdate) -> BomOut:
        bom = await self.repo.get(bom_id)
        if bom is None:
            raise NotFoundException("BOM 不存在")
        if payload.version is not None:
            bom.version = payload.version
        if payload.remark is not None:
            bom.remark = payload.remark
        if payload.items is not None:
            bom.items.clear()
            for item in payload.items:
                bom.items.append(
                    BomItem(
                        component_material_id=item.component_material_id,
                        qty=item.qty,
                        loss_rate=item.loss_rate,
                        seq=item.seq,
                    )
                )
        bom.updated_at = datetime.utcnow()
        await self.session.commit()
        bom = await self.repo.enrich_with_material_info(bom)
        return self._to_out(bom)

    async def activate(self, bom_id: int) -> BomActivateOut:
        bom = await self.repo.get(bom_id)
        if bom is None:
            raise NotFoundException("BOM 不存在")
        deactivated_id: int | None = None
        if not bom.is_active:
            old = await self.repo.get_by_product(bom.product_material_id)
            if old and old.id != bom.id:
                old.is_active = False
                deactivated_id = old.id
            bom.is_active = True
            bom.updated_at = datetime.utcnow()
        await self.session.commit()
        bom = await self.repo.enrich_with_material_info(bom)
        return BomActivateOut(bom=self._to_out(bom), deactivated_id=deactivated_id)

    async def shortage(self, product_material_id: int, order_qty: float) -> ShortageOut:
        bom = await self.repo.get_by_product(product_material_id)
        if bom is None:
            product = await self.material_repo.get_material(product_material_id)
            if product is None:
                raise NotFoundException("产品物料不存在")
            return ShortageOut(
                product_code=product.code,
                product_name=product.name,
                order_qty=order_qty,
                ok=False,
                items=[],
            )
        product = await self.material_repo.get_material(product_material_id)
        comp_ids = [it.component_material_id for it in bom.items]
        avail_map = await self.repo.inventory_available_map(comp_ids)
        shortage_items: list[ShortageItem] = []
        for item in bom.items:
            need = item.qty * order_qty * (1 + item.loss_rate)
            need = round(need, 4)
            available = avail_map.get(item.component_material_id, 0.0)
            shortage = round(max(need - available, 0), 4)
            comp = await self.material_repo.get_material(item.component_material_id)
            comp_code = comp.code if comp else f"ID:{item.component_material_id}"
            comp_name = comp.name if comp else ""
            shortage_items.append(
                ShortageItem(
                    component_material_id=item.component_material_id,
                    component_code=comp_code,
                    component_name=comp_name,
                    need_qty=need,
                    available_qty=round(available, 4),
                    shortage_qty=shortage,
                )
            )
        ok = all(s.shortage_qty == 0 for s in shortage_items)
        return ShortageOut(
            product_code=product.code if product else "",
            product_name=product.name if product else "",
            order_qty=order_qty,
            ok=ok,
            items=shortage_items,
        )

    @staticmethod
    def _to_out(bom: Bom) -> BomOut:
        return BomOut(
            id=bom.id,
            product_material_id=bom.product_material_id,
            product_code=getattr(bom, "product_code", None),
            product_name=getattr(bom, "product_name", None),
            version=bom.version,
            is_active=bom.is_active,
            status=bom.status,
            remark=bom.remark,
            created_at=bom.created_at,
            updated_at=bom.updated_at,
            items=[
                BomItemOut(
                    id=it.id,
                    bom_id=it.bom_id,
                    component_material_id=it.component_material_id,
                    component_code=getattr(it, "component_code", None),
                    component_name=getattr(it, "component_name", None),
                    qty=it.qty,
                    loss_rate=it.loss_rate,
                    seq=it.seq,
                )
                for it in bom.items
            ],
        )
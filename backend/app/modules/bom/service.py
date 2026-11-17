from __future__ import annotations

from datetime import datetime

from decimal import Decimal



from sqlalchemy import select

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

from app.modules.material.models import Material

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

            need = float(item.qty) * order_qty * (1 + float(item.loss_rate))

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

    async def import_boms(self, rows: list[dict]) -> dict:
        created, updated, failed = 0, 0, 0
        errors: list[dict] = []

        product_codes = set()
        component_codes = set()
        for raw in rows:
            pc = (raw.get('product_code') or '').strip()
            cc = (raw.get('component_code') or '').strip()
            if pc: product_codes.add(pc)
            if cc: component_codes.add(cc)
        all_codes = product_codes | component_codes
        if not all_codes:
            return {'created': 0, 'updated': 0, 'failed': 0, 'errors': []}

        mat_rows = (await self.session.execute(
            select(Material.code, Material.id).where(Material.code.in_(all_codes))
        )).all()
        mat_map = {code: mid for code, mid in mat_rows}

        unknown = all_codes - set(mat_map.keys())
        if unknown:
            for code in sorted(unknown):
                errors.append({'row': 0, 'error': f'Unknown material code: {code}'})

        bom_cache: dict[tuple[str, str], int] = {}
        for idx, raw in enumerate(rows, start=2):
            pc = (raw.get('product_code') or '').strip()
            cc = (raw.get('component_code') or '').strip()
            if not pc or not cc:
                failed += 1
                errors.append({'row': idx, 'error': 'product_code/component_code empty'})
                continue
            if pc not in mat_map or cc not in mat_map:
                failed += 1
                continue

            version = (raw.get('version') or 'V1').strip()
            qty_per = Decimal(str(raw.get('qty_per') or raw.get('qty') or 1))
            loss_rate = Decimal(str(raw.get('loss_rate') or 0))
            seq = int(raw.get('seq') or 1)

            try:
                pkey = (pc, version)
                if pkey not in bom_cache:
                    existing = (await self.session.execute(
                        select(Bom).where(
                            Bom.product_material_id == mat_map[pc],
                            Bom.version == version,
                        )
                    )).scalar_one_or_none()
                    if existing:
                        bom_cache[pkey] = existing.id
                    else:
                        new_bom = Bom(
                            product_material_id=mat_map[pc],
                            version=version,
                            is_active=True,
                            status='ACTIVE',
                        )
                        self.session.add(new_bom)
                        await self.session.flush()
                        bom_cache[pkey] = new_bom.id

                bom_id = bom_cache[pkey]
                existing_item = (await self.session.execute(
                    select(BomItem).where(
                        BomItem.bom_id == bom_id,
                        BomItem.component_material_id == mat_map[cc],
                    )
                )).scalar_one_or_none()

                if existing_item:
                    existing_item.qty = qty_per
                    existing_item.loss_rate = loss_rate
                    existing_item.seq = seq
                    updated += 1
                else:
                    new_item = BomItem(
                        bom_id=bom_id,
                        component_material_id=mat_map[cc],
                        qty=qty_per,
                        loss_rate=loss_rate,
                        seq=seq,
                    )
                    self.session.add(new_item)
                    created += 1
            except Exception as e:
                failed += 1
                errors.append({'row': idx, 'error': str(e)})

        await self.session.commit()
        return {'created': created, 'updated': updated, 'failed': failed, 'errors': errors}

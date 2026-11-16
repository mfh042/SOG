from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_operator
from app.core.response import Resp
from app.modules.bom.schemas import (
    BomCreate,
    BomUpdate,
    BomOut,
    BomListOut,
    BomActivateOut,
    ShortageOut,
)
from app.modules.bom.service import BomService

router = APIRouter(prefix="/api/boms", tags=["BOM 物料清单"])


@router.post("", response_model=Resp[BomOut])
async def create(payload: BomCreate, db: AsyncSession = Depends(get_db), _op: str = Depends(get_operator)):
    result = await BomService(db).create(payload)
    return Resp.ok(result)


@router.get("/shortage/{product_material_id}", response_model=Resp[ShortageOut])
async def shortage(
    product_material_id: int,
    qty: float = Query(..., gt=0, description="订单数量"),
    db: AsyncSession = Depends(get_db),
):
    result = await BomService(db).shortage(product_material_id, qty)
    return Resp.ok(result)


@router.get("/{bom_id}", response_model=Resp[BomOut])
async def get(bom_id: int, db: AsyncSession = Depends(get_db)):
    result = await BomService(db).get(bom_id)
    return Resp.ok(result)


@router.get("", response_model=Resp[list[BomListOut]])
async def list(
    product_material_id: int | None = Query(None),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result = await BomService(db).list(product_material_id, keyword)
    return Resp.ok(result)


@router.put("/{bom_id}", response_model=Resp[BomOut])
async def update(bom_id: int, payload: BomUpdate, db: AsyncSession = Depends(get_db), _op: str = Depends(get_operator)):
    result = await BomService(db).update(bom_id, payload)
    return Resp.ok(result)


@router.post("/{bom_id}/activate", response_model=Resp[BomActivateOut])
async def activate(bom_id: int, db: AsyncSession = Depends(get_db), _op: str = Depends(get_operator)):
    result = await BomService(db).activate(bom_id)
    return Resp.ok(result)
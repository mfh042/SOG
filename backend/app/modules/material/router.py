"""物料管控 REST 路由。"""
import csv
import io

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination, get_db, get_operator, get_pagination
from app.core.permissions import require_perm
from app.core.response import PageData, Resp
from app.modules.material.models import Inventory
from app.modules.material.schemas import (
    InventoryOut,
    MaterialIn,
    MaterialOut,
    MaterialUpdate,
    StockAdjust,
    StockIn,
    StockOpReq,
    TxnOut,
)
from app.modules.material.service import MaterialService

router = APIRouter(prefix="/api/materials", tags=["物料管控"])


def _inv_out(inv: Inventory) -> InventoryOut:
    return InventoryOut(
        id=inv.id,
        material_id=inv.material_id,
        batch_no=inv.batch_no,
        location=inv.location,
        qty_on_hand=inv.qty_on_hand,
        qty_reserved=inv.qty_reserved,
        available=inv.available,
        status=inv.status,
    )


@router.post("/import", summary="CSV 批量导入物料主数据")
async def import_materials(
    file: UploadFile = File(...),
    _: dict = Depends(require_perm("material:create")),
    session: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gbk")
    rows = list(csv.DictReader(io.StringIO(text)))
    result = await MaterialService(session).import_materials(rows)
    return Resp.ok(
        result,
        message=f"导入完成：+{result['created']} 跳过 {result['skipped']} 失败 {result['failed']}",
    )


@router.post("", response_model=Resp[MaterialOut], summary="新建物料主数据")
async def create_material(
    payload: MaterialIn,
    _: dict = Depends(require_perm("material:create")),
    session: AsyncSession = Depends(get_db),
):
    m = await MaterialService(session).create_material(payload)
    return Resp.ok(MaterialOut.model_validate(m, from_attributes=True))


@router.get("", response_model=Resp[PageData[MaterialOut]], summary="物料分页列表")
async def list_materials(
    mtype: str | None = Query(None, description="RAW/WIP/FINISHED"),
    keyword: str | None = Query(None, description="编码或名称模糊匹配"),
    page: Pagination = Depends(get_pagination),
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await MaterialService(session).list_materials(mtype, keyword, page)
    return Resp.page(
        [MaterialOut.model_validate(r, from_attributes=True) for r in rows],
        total, page.page, page.size,
    )


@router.post("/inbound", response_model=Resp[InventoryOut], summary="物料入库")
async def inbound(
    payload: StockIn,
    _: dict = Depends(require_perm("inventory:all")),
    session: AsyncSession = Depends(get_db),
    operator: str = Depends(get_operator),
):
    inv = await MaterialService(session, operator).inbound(payload)
    return Resp.ok(_inv_out(inv), message="入库成功")


@router.post("/reserve", response_model=Resp[InventoryOut], summary="预留库存")
async def reserve(
    req: StockOpReq,
    _: dict = Depends(require_perm("inventory:all")),
    session: AsyncSession = Depends(get_db),
    operator: str = Depends(get_operator),
):
    inv = await MaterialService(session, operator).reserve(req)
    return Resp.ok(_inv_out(inv), message="预留成功")


@router.post("/release", response_model=Resp[InventoryOut], summary="释放预留")
async def release(
    req: StockOpReq,
    _: dict = Depends(require_perm("inventory:all")),
    session: AsyncSession = Depends(get_db),
    operator: str = Depends(get_operator),
):
    inv = await MaterialService(session, operator).release(req)
    return Resp.ok(_inv_out(inv), message="已释放预留")


@router.post("/issue", response_model=Resp[InventoryOut], summary="领料出库（不传批次则 FIFO）")
async def issue(
    req: StockOpReq,
    _: dict = Depends(require_perm("inventory:all")),
    session: AsyncSession = Depends(get_db),
    operator: str = Depends(get_operator),
):
    inv = await MaterialService(session, operator).issue(req)
    return Resp.ok(_inv_out(inv), message="出库成功")


@router.post("/scrap", response_model=Resp[InventoryOut], summary="报废出库")
async def scrap(
    req: StockOpReq,
    _: dict = Depends(require_perm("inventory:all")),
    session: AsyncSession = Depends(get_db),
    operator: str = Depends(get_operator),
):
    inv = await MaterialService(session, operator).scrap(req)
    return Resp.ok(_inv_out(inv), message="报废已记录")


@router.post("/adjust", response_model=Resp[InventoryOut], summary="盘盈亏调整")
async def adjust(
    payload: StockAdjust,
    _: dict = Depends(require_perm("inventory:all")),
    session: AsyncSession = Depends(get_db),
    operator: str = Depends(get_operator),
):
    inv = await MaterialService(session, operator).adjust(payload)
    return Resp.ok(_inv_out(inv), message="盘点调整已完成")


@router.get("/inventory", response_model=Resp[PageData[InventoryOut]], summary="库存台账")
async def list_inventory(
    material_id: int | None = Query(None),
    page: Pagination = Depends(get_pagination),
    _: dict = Depends(require_perm("inventory:read")),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await MaterialService(session).list_inventory(material_id, page)
    return Resp.page([_inv_out(r) for r in rows], total, page.page, page.size)


@router.get("/inventory/{inventory_id}", response_model=Resp[InventoryOut], summary="库存行详情")
async def get_inventory(
    inventory_id: int,
    _: dict = Depends(require_perm("inventory:read")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_inv_out(await MaterialService(session).get_inventory(inventory_id)))


@router.get("/transactions", response_model=Resp[list[TxnOut]], summary="出入库流水")
async def list_txn(
    material_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    _: dict = Depends(require_perm("inventory:read")),
    session: AsyncSession = Depends(get_db),
):
    rows = await MaterialService(session).list_txn(material_id, limit)
    return Resp.ok([TxnOut.model_validate(r, from_attributes=True) for r in rows])


@router.get("/low-stock", summary="低库存预警")
async def low_stock(
    _: dict = Depends(require_perm("inventory:read")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(await MaterialService(session).low_stock())


@router.get("/{material_id}", response_model=Resp[MaterialOut], summary="物料详情")
async def get_material(
    material_id: int,
    _: dict = Depends(require_perm("material:read")),
    session: AsyncSession = Depends(get_db),
):
    m = await MaterialService(session).get_material(material_id)
    return Resp.ok(MaterialOut.model_validate(m, from_attributes=True))


@router.put("/{material_id}", response_model=Resp[MaterialOut], summary="更新物料主数据")
async def update_material(
    material_id: int,
    payload: MaterialUpdate,
    _: dict = Depends(require_perm("material:update")),
    session: AsyncSession = Depends(get_db),
):
    m = await MaterialService(session).update_material(material_id, payload)
    return Resp.ok(MaterialOut.model_validate(m, from_attributes=True))


@router.delete("/{material_id}", summary="删除物料主数据")
async def delete_material(
    material_id: int,
    _: dict = Depends(require_perm("material:delete")),
    session: AsyncSession = Depends(get_db),
):
    await MaterialService(session).delete_material(material_id)
    return Resp.ok({"id": material_id})
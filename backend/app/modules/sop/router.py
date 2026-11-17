"""SOP 作业指导 REST 路由。"""
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_perm
from app.core.response import Resp
from app.modules.material.models import Material
from app.modules.sop.models import SopTemplate
from app.modules.sop.schemas import (
    SopCreate, SopOut, SopUpdate,
    TemplateApplyIn, TemplateCreate, TemplateOut, TemplateUpdate,
)
from app.modules.sop.service import SopService

router = APIRouter(prefix="/api/sops", tags=["SOP 作业指导"])

UPLOAD_DIR = Path(os.environ.get("SOP_UPLOAD_DIR", Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "sop"))
ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
ALLOWED_PDF = {"application/pdf"}
ALLOWED_VIDEO = {"video/mp4", "video/webm", "video/ogg", "video/quicktime"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _detect_media_type(content_type: str) -> str | None:
    if content_type in ALLOWED_IMAGE:
        return "image"
    if content_type in ALLOWED_PDF:
        return "pdf"
    if content_type in ALLOWED_VIDEO:
        return "video"
    return None


def _to_out(s) -> SopOut:
    return SopOut.model_validate(s, from_attributes=True)


def _to_tpl(t) -> TemplateOut:
    return TemplateOut.model_validate(t, from_attributes=True)


@router.post("/upload", summary="上传 SOP 媒体文件")
async def upload_file(
    file: UploadFile = File(...),
    _: dict = Depends(require_perm("sop:upload")),
):
    _ensure_upload_dir()
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")
    media_type = _detect_media_type(file.content_type or "")
    if media_type is None:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}。仅支持图片/JPG/PNG、PDF、视频/MP4")
    ext = Path(file.filename).suffix.lower() or ".bin"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / safe_name
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件超过 50MB 限制")
    with open(dest, "wb") as f:
        f.write(content)
    url = f"/uploads/sop/{safe_name}"
    return Resp.ok({
        "url": url,
        "media_type": media_type,
        "filename": file.filename,
        "size": len(content),
    })


@router.get("/files/{filename}", summary="下载/查看 SOP 媒体文件")
async def get_file(
    filename: str,
    _: dict = Depends(require_perm("sop:read")),
):
    _ensure_upload_dir()
    fp = UPLOAD_DIR / filename
    if not fp.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(fp)


@router.get("/dynamic/{product_code}", summary="动态 SOP — 完整工艺路线 + BOM 指引")
async def dynamic_sop(
    product_code: str,
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    from app.modules.bom.models import Bom
    sops = await SopService(session).list_by_product(product_code, active_only=True)

    bom_items_out = []
    mat = await session.scalar(select(Material).where(Material.code == product_code))
    if mat:
        bom = await session.scalar(
            select(Bom).where(Bom.product_material_id == mat.id, Bom.is_active.is_(True))
        )
        if bom:
            from sqlalchemy.orm import selectinload
            from app.modules.bom.models import BomItem
            items_stmt = (
                select(BomItem)
                .where(BomItem.bom_id == bom.id)
                .options(selectinload(BomItem.component))
            )
            items = list((await session.scalars(items_stmt)).all())
            for it in items:
                comp = await session.get(Material, it.component_material_id)
                bom_items_out.append({
                    "material_code": comp.code if comp else None,
                    "material_name": comp.name if comp else None,
                    "qty_per": float(it.qty) if it.qty else 0,
                })

    steps = []
    for s in sops:
        steps.append({
            "operation_seq": s.operation_seq,
            "operation_name": s.operation_name,
            "title": s.title,
            "content": s.content,
            "content_url": s.content_url,
            "media_type": s.media_type,
            "media_url": s.media_url,
            "annotations": s.annotations,
            "version": s.version,
        })

    return Resp.ok({
        "product_code": product_code,
        "product_name": mat.name if mat else None,
        "routing_steps": steps,
        "bom_items": bom_items_out,
    })


@router.post("", response_model=Resp[SopOut], summary="创建/发布 SOP")
async def create_sop(
    payload: SopCreate,
    _: dict = Depends(require_perm("sop:create")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await SopService(session).create(payload)), message="SOP 已创建")


@router.get("", response_model=Resp[list[SopOut]], summary="SOP 列表（按产品/关键词过滤）")
async def list_sops(
    product_code: str | None = Query(None),
    keyword: str | None = Query(None),
    active_only: bool = Query(True),
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    if product_code:
        rows = await SopService(session).list_by_product(product_code, active_only)
    else:
        rows = await SopService(session).list_all(keyword, active_only)
    return Resp.ok([_to_out(r) for r in rows])


@router.get("/{sop_id}", response_model=Resp[SopOut], summary="SOP 详情")
async def get_sop(
    sop_id: int,
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await SopService(session).get(sop_id)))


@router.get("/for-operation/{product_code}/{operation_seq}", response_model=Resp[SopOut], summary="产品工序 SOP 查询")
async def get_for_op(
    product_code: str,
    operation_seq: int,
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await SopService(session).get_for_operation(product_code, operation_seq)))


@router.put("/{sop_id}", response_model=Resp[SopOut], summary="更新 SOP")
async def update_sop(
    sop_id: int,
    payload: SopUpdate,
    _: dict = Depends(require_perm("sop:update")),
    session: AsyncSession = Depends(get_db),
):
    return Resp.ok(_to_out(await SopService(session).update(sop_id, payload)), message="SOP 已更新")


@router.delete("/{sop_id}", summary="停用 SOP")
async def delete_sop(
    sop_id: int,
    _: dict = Depends(require_perm("sop:delete")),
    session: AsyncSession = Depends(get_db),
):
    await SopService(session).delete(sop_id)
    return Resp.ok(message="已停用")


# ============ SOP 模板 CRUD ============

@router.get("/templates/list", response_model=Resp[list[TemplateOut]], summary="模板列表")
async def list_templates(
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    active_only: bool = Query(True),
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(SopTemplate)
    if active_only:
        stmt = stmt.where(SopTemplate.is_active.is_(True))
    if category:
        stmt = stmt.where(SopTemplate.category == category)
    if keyword:
        stmt = stmt.where(
            SopTemplate.name.ilike(f"%{keyword}%")
            | SopTemplate.description.ilike(f"%{keyword}%")
        )
    rows = list((await session.scalars(stmt.order_by(SopTemplate.category, SopTemplate.name))).all())
    return Resp.ok([_to_tpl(r) for r in rows])


@router.get("/templates/{tpl_id}", response_model=Resp[TemplateOut], summary="模板详情")
async def get_template(
    tpl_id: int,
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    t = await session.get(SopTemplate, tpl_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    return Resp.ok(_to_tpl(t))


@router.post("/templates", response_model=Resp[TemplateOut], summary="新建模板")
async def create_template(
    payload: TemplateCreate,
    _: dict = Depends(require_perm("sop:create")),
    session: AsyncSession = Depends(get_db),
):
    t = SopTemplate(**payload.model_dump())
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return Resp.ok(_to_tpl(t), message="模板已创建")


@router.put("/templates/{tpl_id}", response_model=Resp[TemplateOut], summary="更新模板")
async def update_template(
    tpl_id: int,
    payload: TemplateUpdate,
    _: dict = Depends(require_perm("sop:update")),
    session: AsyncSession = Depends(get_db),
):
    t = await session.get(SopTemplate, tpl_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    await session.commit()
    await session.refresh(t)
    return Resp.ok(_to_tpl(t), message="模板已更新")


@router.delete("/templates/{tpl_id}", summary="删除模板（内置模板仅停用）")
async def delete_template(
    tpl_id: int,
    _: dict = Depends(require_perm("sop:delete")),
    session: AsyncSession = Depends(get_db),
):
    t = await session.get(SopTemplate, tpl_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    if t.is_builtin:
        t.is_active = False
        await session.commit()
        return Resp.ok(message="内置模板已停用")
    await session.delete(t)
    await session.commit()
    return Resp.ok(message="模板已删除")


@router.post("/templates/{tpl_id}/apply", summary="应用模板 → 返回预填充 SOP 字段（前端用）")
async def apply_template(
    tpl_id: int,
    payload: TemplateApplyIn,
    _: dict = Depends(require_perm("sop:read")),
    session: AsyncSession = Depends(get_db),
):
    t = await session.get(SopTemplate, tpl_id)
    if not t or not t.is_active:
        raise HTTPException(404, "模板不存在或已停用")

    product_display = payload.product_code
    mat = await session.scalar(select(Material).where(Material.code == payload.product_code))
    if mat:
        product_display = f"{mat.name} ({mat.code})"

    operation_name = payload.operation_name or t.operation_name_default or ""

    title = t.title_template.format(
        product=product_display,
        code=payload.product_code,
        operation=operation_name,
        operation_name=operation_name,
        seq=payload.operation_seq,
    ) if t.title_template else ""

    content = t.content.format(
        product=product_display,
        code=payload.product_code,
        operation=operation_name,
        operation_name=operation_name,
        seq=payload.operation_seq,
    ) if t.content else ""

    return Resp.ok({
        "operation_name": operation_name,
        "title": title,
        "content": content,
        "content_url": t.content_url,
        "version": payload.version,
        "product_code": payload.product_code,
        "operation_seq": payload.operation_seq,
    })
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import OrderStatus
from app.integration.adapters.base import RemoteOrder, RemoteOrderItem
from app.integration.models import ExternalIdMapping, SyncJob
from app.modules.orders.models import OrderItem, SalesOrder

logger = logging.getLogger("delv-sog.integration.sync")


async def sync_orders(
    session: AsyncSession,
    system: str,
    orders: list[RemoteOrder],
    job: SyncJob,
) -> SyncJob:
    job.records_fetched = len(orders)
    created = updated = failed = 0

    for remote in orders:
        try:
            mapping_stmt = select(ExternalIdMapping).where(
                ExternalIdMapping.system == system,
                ExternalIdMapping.data_type == "ORDERS",
                ExternalIdMapping.external_id == remote.external_id,
            )
            mapping = await session.scalar(mapping_stmt)

            if mapping:
                order = await session.get(SalesOrder, mapping.local_id)
                if order:
                    _update_order(order, remote)
                    mapping.last_synced_at = datetime.utcnow()
                    updated += 1
                else:
                    order = _create_order(remote)
                    session.add(order)
                    await session.flush()
                    mapping.local_id = order.id
                    mapping.last_synced_at = datetime.utcnow()
                    updated += 1
            else:
                order = await session.scalar(
                    select(SalesOrder).where(SalesOrder.order_no == remote.order_no)
                )
                if order:
                    _update_order(order, remote)
                    session.add(ExternalIdMapping(
                        system=system,
                        data_type="ORDERS",
                        external_id=remote.external_id,
                        local_table="sales_order",
                        local_id=order.id,
                        external_code=remote.order_no,
                        last_synced_at=datetime.utcnow(),
                    ))
                    updated += 1
                else:
                    order = _create_order(remote)
                    session.add(order)
                    await session.flush()
                    session.add(ExternalIdMapping(
                        system=system,
                        data_type="ORDERS",
                        external_id=remote.external_id,
                        local_table="sales_order",
                        local_id=order.id,
                        external_code=remote.order_no,
                        last_synced_at=datetime.utcnow(),
                    ))
                    created += 1
        except Exception as e:
            failed += 1
            logger.exception("Failed to sync order %s: %s", remote.order_no, e)

    job.records_created = created
    job.records_updated = updated
    job.records_failed = failed
    return job


def _create_order(remote: RemoteOrder) -> SalesOrder:
    planned = None
    if remote.planned_date:
        try:
            planned = datetime.strptime(remote.planned_date[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    order = SalesOrder(
        order_no=remote.order_no,
        customer_name=remote.customer_name,
        product_model=remote.product_model,
        priority=remote.priority,
        status=OrderStatus.DRAFT.value,
        planned_date=planned,
        note=remote.note,
    )
    order.items = [
        OrderItem(
            line_no=it.line_no,
            material_code=it.material_code,
            material_name=it.material_name or it.material_code,
            spec=it.spec,
            qty=it.qty,
            unit=it.unit,
        )
        for it in remote.items
    ]
    if not order.items:
        order.items = [OrderItem(
            line_no=1,
            material_code=remote.product_model or remote.order_no,
            material_name=remote.product_model or remote.order_no,
            qty=1,
            unit="PCS",
        )]
    return order


def _update_order(order: SalesOrder, remote: RemoteOrder) -> None:
    order.customer_name = remote.customer_name
    order.product_model = remote.product_model
    order.priority = remote.priority
    order.note = remote.note or order.note
    if remote.planned_date:
        try:
            order.planned_date = datetime.strptime(remote.planned_date[:10], "%Y-%m-%d").date()
        except Exception:
            pass
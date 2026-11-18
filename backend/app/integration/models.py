from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, TimestampMixin


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    config_value: Mapped[str] = mapped_column(Text, default="")
    value_type: Mapped[str] = mapped_column(String(16), default="string")
    description: Mapped[str | None] = mapped_column(String(256))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExternalIdMapping(Base, TimestampMixin):
    __tablename__ = "ext_id_mapping"
    __table_args__ = (
        Index("ix_ext_mapping_local", "local_table", "local_id"),
        Index("ix_ext_mapping_external", "system", "external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String(16), index=True, comment="ERP/MES/PLM/WMS")
    data_type: Mapped[str] = mapped_column(String(32), index=True, comment="ORDERS/MATERIALS/BOM/...")
    external_id: Mapped[str] = mapped_column(String(128), index=True, comment="外部系统中的 ID")
    local_table: Mapped[str] = mapped_column(String(64), index=True, comment="本地表名")
    local_id: Mapped[int] = mapped_column(index=True, comment="本地记录主键")
    external_code: Mapped[str | None] = mapped_column(String(128), comment="外部编码（如订单号、物料编码）")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncJob(Base):
    __tablename__ = "sync_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String(16), index=True)
    data_type: Mapped[str] = mapped_column(String(32), index=True)
    trigger_type: Mapped[str] = mapped_column(String(16), default="MANUAL", comment="MANUAL/SCHEDULED/EVENT")
    status: Mapped[str] = mapped_column(String(16), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_fetched: Mapped[int] = mapped_column(default=0)
    records_created: Mapped[int] = mapped_column(default=0)
    records_updated: Mapped[int] = mapped_column(default=0)
    records_failed: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    detail_log: Mapped[dict] = mapped_column(JSON, default=dict)
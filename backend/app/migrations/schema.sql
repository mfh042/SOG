-- =====================================================================
-- SOG 离散装配生产作业支援系统  PostgreSQL 18 初始化脚本
-- 模块：订单管理 / 物料管控(原料·在制品·成品·库存) / 生产管理(进度·质量·追溯)
-- 字符集 UTF8；numeric(18,3)；扩展属性使用 JSONB；乐观锁 version。
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------- 订单管理 ----------
CREATE TABLE IF NOT EXISTS sales_order (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_no      VARCHAR(32)  NOT NULL UNIQUE,
    customer_name VARCHAR(128) NOT NULL,
    product_model VARCHAR(128) NOT NULL,
    priority      INTEGER      NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    status        VARCHAR(16)  NOT NULL DEFAULT 'DRAFT'
                  CHECK (status IN ('DRAFT','RELEASED','IN_PROGRESS','COMPLETED','CLOSED','CANCELLED')),
    planned_date  DATE,
    note          TEXT,
    version       INTEGER      NOT NULL DEFAULT 1,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sales_order_status   ON sales_order(status);
CREATE INDEX IF NOT EXISTS idx_sales_order_customer  ON sales_order(customer_name);

CREATE TABLE IF NOT EXISTS order_item (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      BIGINT       NOT NULL REFERENCES sales_order(id) ON DELETE CASCADE,
    line_no       INTEGER      NOT NULL DEFAULT 1,
    material_code VARCHAR(64)  NOT NULL,
    material_name VARCHAR(128) NOT NULL,
    spec          VARCHAR(256),
    qty           NUMERIC(18,3) NOT NULL CHECK (qty > 0),
    unit          VARCHAR(16)  NOT NULL DEFAULT 'PCS',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_order_line UNIQUE (order_id, line_no)
);
CREATE INDEX IF NOT EXISTS idx_order_item_material ON order_item(material_code);

-- ---------- 物料管控：主数据 ----------
CREATE TABLE IF NOT EXISTS material (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         VARCHAR(64)  NOT NULL UNIQUE,
    name         VARCHAR(128) NOT NULL,
    type         VARCHAR(16)  NOT NULL CHECK (type IN ('RAW','WIP','FINISHED')),
    spec         VARCHAR(256),
    unit         VARCHAR(16)  NOT NULL DEFAULT 'PCS',
    safety_stock NUMERIC(18,3) NOT NULL DEFAULT 0 CHECK (safety_stock >= 0),
    status       VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    attrs        JSONB        NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_material_type ON material(type);
CREATE INDEX IF NOT EXISTS idx_material_name  ON material(name);

-- ---------- 物料管控：库存台账 ----------
CREATE TABLE IF NOT EXISTS inventory (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_id   BIGINT       NOT NULL REFERENCES material(id) ON DELETE RESTRICT,
    batch_no      VARCHAR(64)  NOT NULL,
    location      VARCHAR(64)  NOT NULL DEFAULT 'WH-01',
    qty_on_hand   NUMERIC(18,3) NOT NULL DEFAULT 0 CHECK (qty_on_hand >= 0),
    qty_reserved  NUMERIC(18,3) NOT NULL DEFAULT 0 CHECK (qty_reserved >= 0),
    status        VARCHAR(16)  NOT NULL DEFAULT 'AVAILABLE'
                  CHECK (status IN ('AVAILABLE','RESERVED','QUARANTINE')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_inv_batch_loc UNIQUE (material_id, batch_no, location)
);
CREATE INDEX IF NOT EXISTS idx_inv_material ON inventory(material_id);
CREATE INDEX IF NOT EXISTS idx_inv_batch     ON inventory(batch_no);

-- ---------- 物料管控：出入库流水（追溯底账） ----------
CREATE TABLE IF NOT EXISTS stock_transaction (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_id   BIGINT       NOT NULL REFERENCES material(id),
    batch_no      VARCHAR(64)  NOT NULL,
    txn_type      VARCHAR(16)  NOT NULL CHECK (txn_type IN ('IN','RESERVE','RELEASE','OUT','SCRAP')),
    qty           NUMERIC(18,3) NOT NULL,
    balance_after NUMERIC(18,3) NOT NULL,
    ref_type      VARCHAR(32),
    ref_id        BIGINT,
    operator      VARCHAR(64)  NOT NULL DEFAULT 'system',
    remark        TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stxn_material ON stock_transaction(material_id);
CREATE INDEX IF NOT EXISTS idx_stxn_batch    ON stock_transaction(batch_no);
CREATE INDEX IF NOT EXISTS idx_stxn_ref       ON stock_transaction(ref_id);
CREATE INDEX IF NOT EXISTS idx_stxn_created  ON stock_transaction(created_at);

-- ---------- 生产管理：工单 ----------
CREATE TABLE IF NOT EXISTS work_order (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wo_no           VARCHAR(32)  NOT NULL UNIQUE,
    sales_order_id  BIGINT       REFERENCES sales_order(id) ON DELETE SET NULL,
    product_code    VARCHAR(64)  NOT NULL,
    product_name    VARCHAR(128) NOT NULL,
    plan_qty        NUMERIC(18,3) NOT NULL CHECK (plan_qty > 0),
    done_qty        NUMERIC(18,3) NOT NULL DEFAULT 0,
    scrap_qty       NUMERIC(18,3) NOT NULL DEFAULT 0,
    status          VARCHAR(16)  NOT NULL DEFAULT 'PLANNED'
                    CHECK (status IN ('PLANNED','RELEASED','RUNNING','DONE','SCRAPPED')),
    line            VARCHAR(32),
    station         VARCHAR(32),
    route           JSONB        NOT NULL DEFAULT '[]',
    planned_start   TIMESTAMPTZ,
    planned_end     TIMESTAMPTZ,
    version         INTEGER      NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wo_status  ON work_order(status);
CREATE INDEX IF NOT EXISTS idx_wo_product ON work_order(product_code);
CREATE INDEX IF NOT EXISTS idx_wo_order   ON work_order(sales_order_id);

-- ---------- 生产管理：报工进度 ----------
CREATE TABLE IF NOT EXISTS production_progress (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wo_id            BIGINT      NOT NULL REFERENCES work_order(id),
    seq              INTEGER,
    good_qty         NUMERIC(18,3) NOT NULL DEFAULT 0,
    bad_qty          NUMERIC(18,3) NOT NULL DEFAULT 0,
    station          VARCHAR(32),
    operator         VARCHAR(64) NOT NULL DEFAULT 'system',
    note             TEXT,
    idempotency_key  VARCHAR(64),
    logged_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_progress_wo ON production_progress(wo_id);
CREATE INDEX IF NOT EXISTS idx_progress_at ON production_progress(logged_at);
CREATE INDEX IF NOT EXISTS idx_progress_key ON production_progress(wo_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_progress_seq ON production_progress(wo_id, seq);

-- ---------- 生产管理：质量检验 ----------
CREATE TABLE IF NOT EXISTS quality_inspection (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wo_id         BIGINT REFERENCES work_order(id),
    product_code  VARCHAR(64),
    product_batch VARCHAR(64),
    inspect_item  VARCHAR(128) NOT NULL,
    result        VARCHAR(16)  NOT NULL CHECK (result IN ('PASS','FAIL','REWORK')),
    defect_code   VARCHAR(32),
    defect_desc   TEXT,
    defect_images JSONB        NOT NULL DEFAULT '[]',
    inspector     VARCHAR(64)  NOT NULL DEFAULT 'system',
    note          TEXT,
    inspected_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_qi_wo      ON quality_inspection(wo_id);
CREATE INDEX IF NOT EXISTS idx_qi_batch   ON quality_inspection(product_batch);
CREATE INDEX IF NOT EXISTS idx_qi_result  ON quality_inspection(result);
CREATE INDEX IF NOT EXISTS idx_qi_defect  ON quality_inspection(defect_code);
CREATE INDEX IF NOT EXISTS idx_qi_product ON quality_inspection(product_code);

-- ---------- 生产管理：批次追溯链（正向/反向） ----------
CREATE TABLE IF NOT EXISTS trace_record (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wo_id         BIGINT REFERENCES work_order(id),
    product_batch VARCHAR(64),
    material_id   BIGINT REFERENCES material(id),
    material_batch VARCHAR(64),
    event_type    VARCHAR(24) NOT NULL
                  CHECK (event_type IN ('ISSUE_MATERIAL','WORK_START','ASSEMBLE','INSPECT','PACK','SCRAP')),
    qty           NUMERIC(18,3) NOT NULL DEFAULT 0,
    operator      VARCHAR(64)  NOT NULL DEFAULT 'system',
    detail        JSONB        NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_trace_wo      ON trace_record(wo_id);
CREATE INDEX IF NOT EXISTS idx_trace_product ON trace_record(product_batch);
CREATE INDEX IF NOT EXISTS idx_trace_mat     ON trace_record(material_batch);
CREATE INDEX IF NOT EXISTS idx_trace_event   ON trace_record(event_type);

-- 库存一致性视图：可用量 = 在手 - 预留
CREATE OR REPLACE VIEW v_inventory_available AS
SELECT m.code, m.name, m.type, i.batch_no, i.location,
       i.qty_on_hand, i.qty_reserved,
       (i.qty_on_hand - i.qty_reserved) AS qty_available,
       m.safety_stock
FROM inventory i
JOIN material m ON m.id = i.material_id;
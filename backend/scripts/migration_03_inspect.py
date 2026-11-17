"""第 3 批 DB 迁移：检验类型字典 + 工序关联 + 审计日志表。"""
import psycopg

MIGRATION = """
-- ============================================================
-- Migration 03: 检验类型字典 + 工序关联 + 审计日志
-- ============================================================

-- 1) 检验类型字典
CREATE TABLE IF NOT EXISTS inspect_type (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'FQC',
    sample_strategy VARCHAR(32) NOT NULL DEFAULT 'FIXED',
    sample_count INTEGER NOT NULL DEFAULT 5,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2) quality_inspection 扩展：检验类型 + 工序关联
ALTER TABLE quality_inspection ADD COLUMN IF NOT EXISTS inspect_type VARCHAR(32) DEFAULT 'FQC';
ALTER TABLE quality_inspection ADD COLUMN IF NOT EXISTS operation_seq INTEGER;
ALTER TABLE quality_inspection ADD COLUMN IF NOT EXISTS sample_qty INTEGER NOT NULL DEFAULT 1;
ALTER TABLE quality_inspection ADD COLUMN IF NOT EXISTS judge VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_qi_inspect_type ON quality_inspection(inspect_type);
CREATE INDEX IF NOT EXISTS idx_qi_operation_seq ON quality_inspection(operation_seq);

ALTER TABLE quality_inspection ADD CONSTRAINT qi_inspect_type_check
    CHECK (inspect_type IN ('IQC','IPQC','FQC','OQC','PQC','SPQC'));

-- 3) 审计日志
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor_id INTEGER,
    actor_username VARCHAR(64),
    actor_role VARCHAR(32),
    action VARCHAR(64) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    target_id VARCHAR(64),
    detail JSONB NOT NULL DEFAULT '{}',
    result VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    ip VARCHAR(64),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_log(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id);
"""

SEED_INSPECT_TYPES = """
INSERT INTO inspect_type (code, name, category, sample_strategy, sample_count, description) VALUES
('IQC', '来料检验', 'IQC', 'FIXED', 5, '供应商来料入库前检验'),
('IPQC', '制程巡检', 'IPQC', 'INTERVAL', 2, '生产过程定时/定量巡检'),
('PQC', '首件检验', 'PQC', 'FIXED', 1, '换线/换批后首件全检'),
('FQC', '成品检验', 'FQC', 'FIXED', 5, '成品入库前最终检验'),
('OQC', '出货检验', 'OQC', 'FIXED', 5, '出货前抽检，按 AQL 抽样'),
('SPQC', '特殊检验', 'SPQC', 'FIXED', 10, '客户指定或异常追溯的专项检验')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    sample_strategy = EXCLUDED.sample_strategy,
    sample_count = EXCLUDED.sample_count,
    description = EXCLUDED.description;
"""


def main():
    conn = psycopg.connect("postgresql://postgres:123456@127.0.0.1:5432/sog")
    cur = conn.cursor()
    cur.execute(MIGRATION)
    print("✅ Migration applied: inspect_type, qi extensions, audit_log")
    cur.execute(SEED_INSPECT_TYPES)
    print("✅ Seeded 6 default inspect types")
    conn.commit()

    cur.execute("SELECT code, name, category FROM inspect_type ORDER BY code")
    print("\nDefault inspect types:")
    for r in cur.fetchall():
        print(f"  {r[0]:6s} {r[1]:10s} [{r[2]}]")

    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='quality_inspection' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    print(f"\nquality_inspection columns: {cols}")

    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('inspect_type','audit_log')")
    new_tables = [r[0] for r in cur.fetchall()]
    print(f"\nNew tables verified: {new_tables}")

    conn.close()
    print("\nMigration 03 complete!")


main()
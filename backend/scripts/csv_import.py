"""CSV 批量导入工具：物料 + BOM。

用法：
    python scripts/csv_import.py materials.csv
    python scripts/csv_import.py bom.csv --bom-product FG-101812
"""
import asyncio
import csv
import sys
from pathlib import Path

import psycopg


def parse_materials_csv(path: str) -> list[dict]:
    """列：code, name, type, unit, spec, safety_stock, status"""
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "code": r["code"].strip(),
                "name": r["name"].strip(),
                "type": r.get("type", "RAW").strip().upper(),
                "unit": r.get("unit", "PCS").strip(),
                "spec": r.get("spec") or None,
                "safety_stock": float(r.get("safety_stock", 0) or 0),
                "status": r.get("status", "ACTIVE").strip().upper(),
            })
    return rows


def parse_bom_csv(path: str) -> list[dict]:
    """列：product_code, component_code, qty_per, loss_rate"""
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "product_code": r["product_code"].strip(),
                "component_code": r["component_code"].strip(),
                "qty_per": float(r.get("qty_per", 1) or 1),
                "loss_rate": float(r.get("loss_rate", 0) or 0),
            })
    return rows


def import_materials(conn, rows: list[dict]) -> None:
    cur = conn.cursor()
    ok, skip, err = 0, 0, 0
    for r in rows:
        try:
            cur.execute("SELECT id FROM material WHERE code=%s", (r["code"],))
            if cur.fetchone():
                skip += 1
                continue
            cur.execute("""
                INSERT INTO material (code, name, type, unit, spec, safety_stock, status, attrs)
                VALUES (%s, %s, %s, %s, %s, %s, %s, '{}'::jsonb)
            """, (r["code"], r["name"], r["type"], r["unit"], r["spec"], r["safety_stock"], r["status"]))
            ok += 1
        except Exception as e:
            err += 1
            print(f"  ERR material {r['code']}: {e}")
    conn.commit()
    print(f"Materials: +{ok} skipped={skip} errors={err}")


def import_bom(conn, rows: list[dict]) -> None:
    cur = conn.cursor()
    ok, skip, err = 0, 0, 0

    products = set(r["product_code"] for r in rows)
    components = set(r["component_code"] for r in rows)

    cur.execute("SELECT code, id FROM material WHERE code = ANY(%s)", (list(products | components),))
    mat_map = {code: mid for code, mid in cur.fetchall()}

    bom_cache: dict[str, int] = {}
    for r in rows:
        try:
            pcode = r["product_code"]
            ccode = r["component_code"]
            if pcode not in mat_map:
                err += 1
                print(f"  ERR unknown product {pcode}")
                continue
            if ccode not in mat_map:
                err += 1
                print(f"  ERR unknown component {ccode}")
                continue

            if pcode not in bom_cache:
                cur.execute("SELECT id FROM bom WHERE product_material_id=%s AND is_active=TRUE", (mat_map[pcode],))
                row = cur.fetchone()
                if row:
                    bom_cache[pcode] = row[0]
                else:
                    cur.execute("""
                        INSERT INTO bom (product_material_id, bom_no, version, is_active)
                        VALUES (%s, 'AUTO-' || %s, 1, TRUE)
                        RETURNING id
                    """, (mat_map[pcode], pcode))
                    bom_cache[pcode] = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO bom_item (bom_id, component_material_id, qty_per, loss_rate)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (bom_cache[pcode], mat_map[ccode], r["qty_per"], r["loss_rate"]))
            ok += 1
        except Exception as e:
            err += 1
            print(f"  ERR BOM {r['product_code']}->{r['component_code']}: {e}")

    conn.commit()
    print(f"BOM items: +{ok} errors={err}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python csv_import.py <file.csv> [--bom-product CODE]")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"File not found: {path}")
        sys.exit(1)

    is_bom = "--bom" in path.lower() or "bom" in path.lower()
    for arg in sys.argv[2:]:
        if arg.startswith("--bom-product"):
            is_bom = True

    conn = psycopg.connect("postgresql://postgres:123456@127.0.0.1:5432/sog")
    try:
        if is_bom:
            rows = parse_bom_csv(path)
            import_bom(conn, rows)
        else:
            rows = parse_materials_csv(path)
            import_materials(conn, rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
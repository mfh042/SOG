"""SOG 后端端到端冒烟测试（接口层）。

运行：python smoke_test.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
STAMP = time.strftime("%H%M%S")
ok = 0
fail = 0
failures: list[str] = []


def _call(path: str, body: dict | None = None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    if payload.get("code") != 0:
        raise RuntimeError(f"code={payload.get('code')} msg={payload.get('message')}")
    return payload.get("data")


def post(path: str, body: dict | None = None):
    return _call(path, body if body is not None else {})


def get(path: str):
    return _call(path, None)


def step(name: str):
    def deco(fn):
        global ok, fail
        try:
            fn()
            print(f"[PASS] {name}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {name} -> {type(e).__name__}: {e}")
            failures.append(name)
            fail += 1
        return fn

    return deco


ctx: dict = {}


@step("健康检查")
def _():
    h = get("/health")
    assert h["status"] == "up", h


@step("创建原料物料")
def _():
    ctx["m1"] = post(
        "/api/materials",
        {
            "code": f"RM-{STAMP}",
            "name": "螺栓 M8",
            "type": "RAW",
            "spec": "M8x30",
            "unit": "PCS",
            "safety_stock": 50,
        },
    )
    assert ctx["m1"]["id"]


@step("创建成品物料")
def _():
    ctx["m2"] = post(
        "/api/materials",
        {
            "code": f"FG-{STAMP}",
            "name": "减速箱总成",
            "type": "FINISHED",
            "spec": "GB-100",
            "unit": "PCS",
            "safety_stock": 0,
        },
    )
    assert ctx["m2"]["id"]


@step("原料入库")
def _():
    ctx["batch"] = f"B-RM-{STAMP}"
    post(
        "/api/materials/inbound",
        {
            "material_id": ctx["m1"]["id"],
            "batch_no": ctx["batch"],
            "location": "WH-A1",
            "qty": 500,
        },
    )


@step("物料详情")
def _():
    get(f"/api/materials/{ctx['m1']['id']}")


@step("物料列表分页")
def _():
    p = get("/api/materials?page=1&size=10")
    assert p["total"] >= 1, p


@step("库存台账分页")
def _():
    ctx["inv"] = get("/api/materials/inventory?page=1&size=50")
    assert len(ctx["inv"]["items"]) >= 1, ctx["inv"]


@step("库存行明细")
def _():
    get(f"/api/materials/inventory/{ctx['inv']['items'][0]['id']}")


@step("低库存预警")
def _():
    get("/api/materials/low-stock")


@step("创建订单")
def _():
    ctx["o"] = post(
        "/api/orders",
        {
            "customer_name": f"客户-{STAMP}",
            "product_model": "GB-100",
            "priority": 2,
            "planned_date": "2026-11-20",
            "note": "冒烟",
            "items": [
                {
                    "material_code": ctx["m2"]["code"],
                    "material_name": "减速箱总成",
                    "qty": 10,
                    "unit": "PCS",
                }
            ],
        },
    )
    assert ctx["o"]["id"]


@step("释放订单生成工单")
def _():
    ctx["rel"] = post(f"/api/orders/{ctx['o']['id']}/release")
    assert ctx["rel"]["work_orders"], ctx["rel"]
    ctx["wo"] = ctx["rel"]["work_orders"][0]


@step("重复释放幂等")
def _():
    again = post(f"/api/orders/{ctx['o']['id']}/release")
    assert len(again["work_orders"]) == len(ctx["rel"]["work_orders"])


@step("订单关联工单")
def _():
    get(f"/api/orders/{ctx['o']['id']}/work-orders")


@step("按单号查订单")
def _():
    get(f"/api/orders/no/{ctx['o']['order_no']}")


@step("工单下达")
def _():
    t = post(f"/api/production/work-orders/{ctx['wo']['id']}/transition?target=RELEASED")
    assert t["status"] == "RELEASED", t


@step("工单开工")
def _():
    t = post(f"/api/production/work-orders/{ctx['wo']['id']}/transition?target=RUNNING")
    assert t["status"] == "RUNNING", t


@step("查询工序进度")
def _():
    ctx["ops"] = get(f"/api/production/work-orders/{ctx['wo']['id']}/operations")
    assert isinstance(ctx["ops"], list) and len(ctx["ops"]) >= 1, ctx["ops"]


@step("首道工序报工（含领料出库）")
def _():
    ctx["r1"] = post(
        f"/api/production/work-orders/{ctx['wo']['id']}/report",
        {
            "seq": ctx["ops"][0]["seq"],
            "good_qty": 10,
            "bad_qty": 0,
            "station": "ST-01",
            "idempotency_key": f"S1-{ctx['wo']['id']}",
            "materials": [
                {"material_id": ctx["m1"]["id"], "qty": 10},
            ],
        },
    )


@step("同幂等键重复提交被忽略")
def _():
    dup = post(
        f"/api/production/work-orders/{ctx['wo']['id']}/report",
        {
            "seq": ctx["ops"][0]["seq"],
            "good_qty": 10,
            "bad_qty": 0,
            "station": "ST-01",
            "idempotency_key": f"S1-{ctx['wo']['id']}",
        },
    )
    assert dup["duplicated"] is True, dup


@step("其余工序报工至末道")
def _():
    fin = None
    for i in range(1, len(ctx["ops"])):
        res = post(
            f"/api/production/work-orders/{ctx['wo']['id']}/report",
            {
                "seq": ctx["ops"][i]["seq"],
                "good_qty": 10,
                "bad_qty": 0,
                "station": "ST-02",
                "idempotency_key": f"S{i + 1}-{ctx['wo']['id']}",
            },
        )
        if i == len(ctx["ops"]) - 1:
            fin = res
    ctx["fin"] = fin


@step("末道完工自动入成品仓")
def _():
    assert ctx["fin"]["finished"] is True, ctx["fin"]
    ctx["fg_batch"] = ctx["fin"]["finished_batch"]
    inv = get(f"/api/materials/inventory?material_id={ctx['m2']['id']}&page=1&size=20")
    assert any(i["batch_no"] == ctx["fg_batch"] for i in inv["items"]), ctx["fg_batch"]


@step("工单状态为 DONE")
def _():
    w = get(f"/api/production/work-orders/{ctx['wo']['id']}")
    assert w["status"] == "DONE", w


@step("报工流水查询")
def _():
    get(f"/api/production/progress?wo_id={ctx['wo']['id']}")


@step("录入质量检验")
def _():
    post(
        "/api/production/inspections",
        {
            "wo_id": ctx["wo"]["id"],
            "product_code": ctx["m2"]["code"],
            "product_batch": ctx["fg_batch"],
            "inspect_item": "外观",
            "result": "PASS",
        },
    )


@step("质量统计")
def _():
    s = get("/api/production/inspections/stats")
    assert s, s


@step("检验记录分页")
def _():
    get("/api/production/inspections?page=1&size=10")


@step("正向追溯（成品批次）")
def _():
    f = get(f"/api/production/trace/forward/{ctx['fg_batch']}")
    assert len(f["events"]) >= 1, f


@step("反向追溯（原料批次）")
def _():
    b = get(f"/api/production/trace/backward/{ctx['batch']}")
    assert len(b["events"]) >= 1, b


@step("追溯树")
def _():
    t = get(f"/api/production/trace/tree/{ctx['fg_batch']}")
    assert t.get("work_orders"), t


@step("追溯事件列表")
def _():
    get("/api/production/trace?limit=50")


@step("出入库流水")
def _():
    get("/api/materials/transactions?limit=50")


@step("预留库存")
def _():
    post(
        "/api/materials/reserve",
        {
            "material_id": ctx["m1"]["id"],
            "batch_no": ctx["batch"],
            "location": "WH-A1",
            "qty": 20,
        },
    )


@step("释放预留")
def _():
    post(
        "/api/materials/release",
        {
            "material_id": ctx["m1"]["id"],
            "batch_no": ctx["batch"],
            "location": "WH-A1",
            "qty": 20,
        },
    )


@step("报废出库")
def _():
    post(
        "/api/materials/scrap",
        {
            "material_id": ctx["m1"]["id"],
            "batch_no": ctx["batch"],
            "location": "WH-A1",
            "qty": 2,
        },
    )


@step("FIFO 出库（不指定批次）")
def _():
    post("/api/materials/issue", {"material_id": ctx["m1"]["id"], "qty": 1})


print()
if fail == 0:
    print(f"==== 全部通过：{ok} 项 ====")
else:
    print(f"==== 通过 {ok} / 失败 {fail} ====")
    print("失败项：" + ", ".join(failures))
    sys.exit(1)
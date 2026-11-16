$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8000'
$script:ok = 0; $script:fail = 0
$stamp = (Get-Date -Format 'HHmmss')

function Step($name, $script) {
  try { & $script; Write-Host "[PASS] $name" -ForegroundColor Green; $script:ok++ }
  catch { Write-Host "[FAIL] $name -> $($_.Exception.Message)" -ForegroundColor Red; $script:fail++ }
}
function Post($path, $body) {
  $r = Invoke-RestMethod -Uri "$base$path" -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 8) -TimeoutSec 20
  if ($r.code -ne 0) { throw "code=$($r.code) $($r.message)" }
  return $r.data
}
function Get($path) {
  $r = Invoke-RestMethod -Uri "$base$path" -TimeoutSec 20
  if ($r.code -ne 0) { throw "code=$($r.code) $($r.message)" }
  return $r.data
}

Step '健康检查' { (Invoke-RestMethod -Uri "$base/health" -TimeoutSec 10).data.status | Out-Null }

Step '创建原料物料 RM' {
  $script:m1 = Post '/api/materials' @{ code="RM-$stamp"; name='螺栓 M8'; type='RAW'; spec='M8x30'; unit='PCS'; safety_stock=50 }
  if (-not $script:m1.id) { throw 'no id' }
}
Step '创建成品物料 FG' {
  $script:m2 = Post '/api/materials' @{ code="FG-$stamp"; name='减速箱总成'; type='FINISHED'; spec='GB-100'; unit='PCS'; safety_stock=0 }
}
Step '原料入库 500' {
  $script:bNo = "B-RM-$stamp"
  Post '/api/materials/inbound' @{ material_id=$script:m1.id; batch_no=$script:bNo; location='WH-A1'; qty=500 } | Out-Null
}
Step '物料详情' { Get "/api/materials/$($script:m1.id)" | Out-Null }
Step '物料列表分页' {
  $p = Get "/api/materials?page=1&size=10"
  if ($p.total -lt 1) { throw 'total=0' }
}
Step '库存台账分页' {
  $script:inv = Get "/api/materials/inventory?page=1&size=50"
  if ($script:inv.items.Count -lt 1) { throw 'no inventory' }
}
Step '库存行明细' { Get "/api/materials/inventory/$($script:inv.items[0].id)" | Out-Null }
Step '低库存预警' { Get '/api/materials/low-stock' | Out-Null }

Step '创建订单（含订单行）' {
  $script:o = Post '/api/orders' @{
    customer_name="客户-$stamp"; product_model='GB-100'; priority=2; planned_date='2026-11-20'; note='冒烟'
    items=@(@{ material_code=$script:m2.code; material_name='减速箱总成'; qty=10; unit='PCS' })
  }
  if (-not $script:o.id) { throw 'no order id' }
}
Step '释放订单生成工单' {
  $script:rel = Post "/api/orders/$($script:o.id)/release" @{}
  if ($script:rel.work_orders.Count -lt 1) { throw 'no work order' }
  $script:wo = $script:rel.work_orders[0]
}
Step '重复释放幂等' {
  $again = Post "/api/orders/$($script:o.id)/release" @{}
  if ($again.work_orders.Count -ne $script:rel.work_orders.Count) { throw 'idempotency broken' }
}
Step '订单关联工单' { Get "/api/orders/$($script:o.id)/work-orders" | Out-Null }
Step '按单号查订单' { Get "/api/orders/no/$($script:o.order_no)" | Out-Null }

Step '工单下达（Query 参数）' {
  $t = Post "/api/production/work-orders/$($script:wo.id)/transition?target=RELEASED" @{}
  if ($t.status -ne 'RELEASED') { throw "status=$($t.status)" }
}
Step '工单开工' {
  $t2 = Post "/api/production/work-orders/$($script:wo.id)/transition?target=RUNNING" @{}
  if ($t2.status -ne 'RUNNING') { throw "status=$($t2.status)" }
}
Step '查询工序进度' {
  $script:ops = Get "/api/production/work-orders/$($script:wo.id)/operations"
  if ($script:ops.Count -lt 1) { throw 'no operations' }
}
Step '首道工序报工' {
  $script:r1 = Post "/api/production/work-orders/$($script:wo.id)/report" @{
    seq=$script:ops[0].seq; good_qty=10; bad_qty=0; station='ST-01'
    idempotency_key="S1-$($script:wo.id)"
  }
}
Step '同幂等键重复提交被忽略' {
  $dup = Post "/api/production/work-orders/$($script:wo.id)/report" @{
    seq=$script:ops[0].seq; good_qty=10; bad_qty=0; station='ST-01'
    idempotency_key="S1-$($script:wo.id)"
  }
  if (-not $dup.duplicated) { throw 'not flagged as duplicated' }
}
Step '其余工序报工至末道' {
  for ($i = 1; $i -lt $script:ops.Count; $i++) {
    $res = Post "/api/production/work-orders/$($script:wo.id)/report" @{
      seq=$script:ops[$i].seq; good_qty=10; bad_qty=0; station='ST-02'
      idempotency_key="S$($i+1)-$($script:wo.id)"
    }
    if ($i -eq $script:ops.Count - 1) { $script:fin = $res }
  }
}
Step '末道完工自动入成品仓' {
  if (-not $script:fin.finished) { throw 'finished flag not set' }
  $script:fgBatch = $script:fin.finished_batch
  $inv2 = Get "/api/materials/inventory?material_id=$($script:m2.id)&page=1&size=20"
  $fg = $inv2.items | Where-Object { $_.batch_no -eq $script:fgBatch }
  if (-not $fg) { throw "成品批次 $($script:fgBatch) 未入库" }
}
Step '工单状态为 DONE' {
  $w = Get "/api/production/work-orders/$($script:wo.id)"
  if ($w.status -ne 'DONE') { throw "status=$($w.status)" }
}
Step '报工流水查询' { Get "/api/production/progress?wo_id=$($script:wo.id)" | Out-Null }

Step '录入质量检验' {
  Post '/api/production/inspections' @{
    wo_id=$script:wo.id; product_code=$script:m2.code; product_batch=$script:fgBatch
    inspect_item='外观'; result='PASS'
  } | Out-Null
}
Step '质量统计' {
  $s = Get '/api/production/inspections/stats'
  if (-not $s.by_result) { throw 'no by_result' }
}
Step '检验记录分页' { Get "/api/production/inspections?page=1&size=10" | Out-Null }
Step '正向追溯（成品批次）' {
  $f = Get "/api/production/trace/forward/$($script:fgBatch)"
  if ($f.events.Count -lt 1) { throw 'no events' }
}
Step '反向追溯（原料批次）' {
  $b = Get "/api/production/trace/backward/$($script:bNo)"
  if ($b.events.Count -lt 1) { throw 'no events' }
}
Step '追溯树' {
  $t = Get "/api/production/trace/tree/$($script:fgBatch)"
  if ($t.work_orders.Count -lt 1) { throw 'no work orders in tree' }
}
Step '追溯事件列表' { Get '/api/production/trace?limit=50' | Out-Null }
Step '出入库流水' { Get '/api/materials/transactions?limit=50' | Out-Null }

Step '预留库存' { Post '/api/materials/reserve' @{ material_id=$script:m1.id; batch_no=$script:bNo; location='WH-A1'; qty=20 } | Out-Null }
Step '释放预留' { Post '/api/materials/release' @{ material_id=$script:m1.id; batch_no=$script:bNo; location='WH-A1'; qty=20 } | Out-Null }
Step '报废出库' { Post '/api/materials/scrap' @{ material_id=$script:m1.id; batch_no=$script:bNo; location='WH-A1'; qty=2 } | Out-Null }
Step 'FIFO 出库（不指定批次）' {
  Post '/api/materials/issue' @{ material_id=$script:m1.id; qty=1 } | Out-Null
}

Write-Host ""
if ($script:fail -eq 0) {
  Write-Host "==== 全部通过：$($script:ok) 项 ====" -ForegroundColor Green
} else {
  Write-Host "==== 通过 $($script:ok) / 失败 $($script:fail) ====" -ForegroundColor Yellow
}
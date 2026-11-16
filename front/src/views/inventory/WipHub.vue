<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { wipSummary, listWorkOrders, getWorkOrder, reportWo, transitionWo, scrapWo, listProgress, listOperations } from '@/api/production'

const route = useRoute()
const router = useRouter()

const activeTab = ref(route.query.tab || 'dashboard')
const loading = ref(false)
const summary = ref(null)
const wipRows = ref([])
const progressRows = ref([])
const currentWo = ref(null)
const operations = ref([])

const tabs = [
  { name: 'dashboard', label: '📊 WIP 看板' },
  { name: 'ledger',    label: '📋 在制台账' },
  { name: 'report',    label: '📥 工序报工' },
  { name: 'aging',     label: '⏱️ 龄分析' },
]

function onTabChange(name) {
  activeTab.value = name
  router.replace({ query: { ...route.query, tab: name } })
}

async function loadAll() {
  loading.value = true
  try {
    const [s, wo] = await Promise.all([
      wipSummary().catch(() => null),
      listWorkOrders({ size: 200 }).catch(() => null),
    ])
    summary.value = s
    wipRows.value = (wo?.items || []).filter(r => ['RELEASED', 'RUNNING'].includes(r.status))
  } catch (e) {
    ElMessage.error('WIP 数据加载失败: ' + (e?.message || e))
  } finally { loading.value = false }
}

watch(activeTab, (v) => {
  if (v === 'progress' || v === 'report' || v === 'ledger') loadAll()
})

const maxStationWip = computed(() => {
  const arr = summary.value?.stations || []
  return arr.length ? Math.max(...arr.map(s => s.wip_qty)) : 1
})

const statusMap = {
  PLANNED:  { text: '待下达', type: 'info' },
  RELEASED: { text: '已下达', type: 'primary' },
  RUNNING:  { text: '生产中', type: 'success' },
  DONE:     { text: '已完工', type: 'success' },
  SCRAPPED: { text: '已报废', type: 'danger' },
}
const statusTag = (s) => statusMap[s] || { text: s, type: 'info' }
const rateColor = (r) => r >= 80 ? '#22c55e' : r >= 50 ? '#2b7cff' : r >= 20 ? '#eab308' : '#f56c6c'

const agingBuckets = computed(() => {
  const rows = wipRows.value.filter(r => r.planned_start)
  const buckets = { '0-12h': 0, '12-24h': 0, '24-48h': 0, '48-72h': 0, '>72h': 0 }
  const now = new Date()
  rows.forEach(r => {
    const h = (now - new Date(r.planned_start)).getTime() / 3600000
    if (h <= 12) buckets['0-12h']++
    else if (h <= 24) buckets['12-24h']++
    else if (h <= 48) buckets['24-48h']++
    else if (h <= 72) buckets['48-72h']++
    else buckets['>72h']++
  })
  return Object.entries(buckets).map(([k, v]) => ({ label: k, count: v }))
})

async function selectWo(row) {
  currentWo.value = row
  try {
    const [ops, prog] = await Promise.all([
      listOperations(row.id).catch(() => []),
      listProgress({ wo_id: row.id, limit: 50 }).catch(() => []),
    ])
    operations.value = ops || []
    progressRows.value = prog?.items || prog || []
  } catch (e) { /* ignore */ }
}

async function doReport(payload) {
  try {
    await reportWo(currentWo.value.id, payload)
    ElMessage.success('报工成功')
    await selectWo(currentWo.value)
    await loadAll()
  } catch (e) {
    ElMessage.error('报工失败: ' + (e?.message || e))
  }
}

async function doFinish(row) {
  await ElMessageBox.confirm(`确认将 ${row.wo_no} 标记完工？`, '完工确认', { type: 'warning' })
  try {
    await transitionWo(row.id, 'DONE')
    ElMessage.success('完工已登记')
    await loadAll()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function doScrap(row) {
  await ElMessageBox.confirm(`确认报废 ${row.wo_no}？`, '报废确认', { type: 'error' })
  try {
    await scrapWo(row.id, { reason: '人工报废登记', qty: 1 })
    ElMessage.success('报废已登记')
    await loadAll()
  } catch (e) {
    ElMessage.error('报废失败')
  }
}

onMounted(loadAll)

const searchWo = ref('')
const reporting = ref(false)
const reportForm = reactive({ seq: 1, good_qty: 0, bad_qty: 0, station: '', note: '', idempotency_key: '' })

async function submitReport() {
  if (!currentWo.value) return ElMessage.warning('请先选择工单')
  if (reportForm.good_qty <= 0 && reportForm.bad_qty <= 0) return ElMessage.warning('请填写报工数量')
  reporting.value = true
  try {
    await doReport({
      seq: reportForm.seq,
      good_qty: reportForm.good_qty,
      bad_qty: reportForm.bad_qty,
      station: reportForm.station || currentWo.value.station,
      note: reportForm.note,
      idempotency_key: reportForm.idempotency_key || undefined,
    })
    reportForm.good_qty = 0
    reportForm.bad_qty = 0
  } finally { reporting.value = false }
}
</script>

<template>
  <div class="hub" v-loading="loading">
    <div class="hub-header">
      <div class="hub-title-row">
        <span class="hub-title">在制品管理中心</span>
        <el-tag type="success" effect="dark" class="hub-tag">WIP</el-tag>
        <el-tag size="small" effect="plain">生产中 {{ wipRows.length }} 单</el-tag>
      </div>
      <div class="hub-sub">看板总览 · 在制台账 · 工序报工 · 龄分析 — 四合一综合操作台</div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange" class="hub-tabs">
      <el-tab-pane v-for="t in tabs" :key="t.name" :name="t.name">
        <template #label><span class="tab-label">{{ t.label }}</span></template>
      </el-tab-pane>
    </el-tabs>

    <div class="hub-content">

      <!-- ================= Tab 1: WIP 看板 ================= -->
      <template v-if="activeTab === 'dashboard'">
        <el-row :gutter="14" class="kpi-row">
          <el-col :span="4" v-for="k in [
            { icon: '📦', label: '在制工单', val: summary?.total_wip_wo ?? 0, unit: '张', cls: 'kpi-blue' },
            { icon: '🔄', label: '在制数量', val: (summary?.wip_qty ?? 0).toFixed(2), unit: '台', cls: 'kpi-cyan' },
            { icon: '✅', label: '平均完工率', val: summary?.avg_done_rate ?? 0, unit: '%', cls: 'kpi-green' },
            { icon: '⚠️', label: '瓶颈工位', val: summary?.bottleneck_station || '-', unit: '', cls: 'kpi-orange', sub: `在制 ${(summary?.bottleneck_wip_qty ?? 0).toFixed(0)} 台`, big: false },
            { icon: '⏰', label: '超龄预警', val: summary?.overdue_wip_count ?? 0, unit: '单', cls: 'kpi-red', sub: '超过 24h 未完工' },
            { icon: '🏭', label: '覆盖工位', val: summary?.stations?.length ?? 0, unit: '个', cls: 'kpi-purple' },
          ]" :key="k.label">
            <div class="kpi-card" :class="k.cls">
              <div class="kpi-icon">{{ k.icon }}</div>
              <div class="kpi-content">
                <div class="kpi-label">{{ k.label }}</div>
                <div class="kpi-value" :class="{ small: k.big === false }">{{ k.val }}<span class="unit">{{ k.unit }}</span></div>
                <div class="kpi-sub" v-if="k.sub">{{ k.sub }}</div>
              </div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="14">
          <el-col :span="15">
            <el-card class="sec">
              <template #header><span class="sec-title">🏭 工位 WIP 分布（按在制量排序）</span></template>
              <div v-if="!summary?.stations?.length" class="empty">暂无在制品数据</div>
              <div v-for="s in (summary?.stations || [])" :key="s.station" class="s-row">
                <div class="s-head">
                  <span class="s-name">{{ s.station }}</span>
                  <span class="s-meta">
                    <el-tag size="small" effect="plain">{{ s.wo_count }} 工单</el-tag>
                    在制 <b>{{ s.wip_qty.toFixed(1) }}</b> · 平均 <b>{{ s.avg_aging_hours }}h</b>
                  </span>
                </div>
                <div class="s-bar">
                  <div class="s-fill" :style="{ width: `${(s.wip_qty / maxStationWip) * 100}%`, background: `linear-gradient(90deg, ${rateColor(s.done_rate)}, ${rateColor(s.done_rate)}aa)` }"></div>
                  <span class="s-lbl">完工率 {{ s.done_rate }}%</span>
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="9">
            <el-card class="sec">
              <template #header>
                <div class="sec-head">
                  <span class="sec-title">⚠️ 超龄预警（>24h）</span>
                  <el-tag v-if="summary?.overdue_wip_count" type="danger" size="small" effect="dark">{{ summary.overdue_wip_count }} 项</el-tag>
                </div>
              </template>
              <div v-if="!summary?.aging_wips?.length" class="empty green">✓ 全部在制品龄正常</div>
              <div v-for="w in (summary?.aging_wips || []).slice(0, 10)" :key="w.wo_id" class="age-item">
                <div class="age-l" :class="w.aging_hours > 72 ? 'danger' : w.aging_hours > 48 ? 'warning' : 'info'">
                  {{ w.aging_hours > 72 ? '🔥' : w.aging_hours > 48 ? '⚠️' : '⏰' }}
                </div>
                <div class="age-b">
                  <div class="age-top">
                    <span class="age-wo">{{ w.wo_no }}</span>
                    <el-tag size="small" :type="statusTag(w.status).type" effect="plain">{{ statusTag(w.status).text }}</el-tag>
                  </div>
                  <div class="age-prod">{{ w.product_name || w.product_code }}</div>
                  <div class="age-meta">工位 <b>{{ w.station || '-' }}</b> · 剩余 <b>{{ w.wip_qty.toFixed(1) }}</b> 台 ·
                    <span :style="{ color: w.aging_hours > 48 ? '#f56c6c' : '#eab308', fontWeight: 600 }">已 {{ w.aging_hours }}h</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </template>

      <!-- ================= Tab 2: 在制台账 ================= -->
      <template v-else-if="activeTab === 'ledger'">
        <div class="ledger-toolbar">
          <el-tag size="small" effect="plain">共 {{ wipRows.length }} 条在制工单</el-tag>
          <el-button size="small" @click="loadAll">刷新</el-button>
        </div>

        <el-table :data="wipRows" border stripe>
          <el-table-column prop="wo_no" label="工单号" width="160" fixed="left">
            <template #default="{ row }"><span class="link" @click="selectWo(row)">{{ row.wo_no }}</span></template>
          </el-table-column>
          <el-table-column label="产品" width="180">
            <template #default="{ row }">
              <div>{{ row.product_code }}</div>
              <div class="sub">{{ row.product_name }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="station" label="工位" width="100">
            <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.station || '-' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="进度" width="260">
            <template #default="{ row }">
              <div class="qty-line">
                <span class="qty-p">计划 {{ Number(row.plan_qty).toFixed(0) }}</span>
                <span class="qty-d">完工 {{ Number(row.done_qty).toFixed(0) }}</span>
                <span class="qty-w">在制 <b>{{ (Number(row.plan_qty) - Number(row.done_qty)).toFixed(0) }}</b></span>
              </div>
              <el-progress :percentage="row.plan_qty ? Math.round(row.done_qty / row.plan_qty * 100) : 0" :stroke-width="10" :color="rateColor(row.plan_qty ? row.done_qty / row.plan_qty * 100 : 0)" />
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }"><el-tag size="small" :type="statusTag(row.status).type" effect="dark">{{ statusTag(row.status).text }}</el-tag></template>
          </el-table-column>
          <el-table-column label="计划时间" width="200">
            <template #default="{ row }">
              <div class="sub">{{ row.planned_start?.slice(0, 16) || '-' }}</div>
              <div class="sub muted">→ {{ row.planned_end?.slice(0, 16) || '-' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="selectWo(row); activeTab='report'">报工</el-button>
              <el-button size="small" type="success" link @click="doFinish(row)">完工</el-button>
              <el-button size="small" type="danger" link @click="doScrap(row)">报废</el-button>
              <el-button size="small" link @click="selectWo(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-card v-if="currentWo" class="detail-card">
          <template #header>
            <div class="sec-head">
              <span class="sec-title">📄 工单详情 · {{ currentWo.wo_no }}</span>
              <el-button size="small" link @click="currentWo = null">关闭</el-button>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="产品">{{ currentWo.product_code }} / {{ currentWo.product_name }}</el-descriptions-item>
                <el-descriptions-item label="工位">{{ currentWo.station || '-' }}</el-descriptions-item>
                <el-descriptions-item label="产线">{{ currentWo.line || '-' }}</el-descriptions-item>
                <el-descriptions-item label="状态"><el-tag :type="statusTag(currentWo.status).type" size="small">{{ statusTag(currentWo.status).text }}</el-tag></el-descriptions-item>
              </el-descriptions>
            </el-col>
            <el-col :span="8">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="计划数量">{{ currentWo.plan_qty }}</el-descriptions-item>
                <el-descriptions-item label="已完工">{{ currentWo.done_qty }}</el-descriptions-item>
                <el-descriptions-item label="已报废">{{ currentWo.scrap_qty }}</el-descriptions-item>
                <el-descriptions-item label="计划开始">{{ currentWo.planned_start?.slice(0, 16) || '-' }}</el-descriptions-item>
              </el-descriptions>
            </el-col>
            <el-col :span="8">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="工艺路线">
                  <div v-if="currentWo.route?.length">
                    <el-tag v-for="(r, i) in currentWo.route" :key="i" size="small" style="margin:2px">{{ r }}</el-tag>
                  </div>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item label="计划结束">{{ currentWo.planned_end?.slice(0, 16) || '-' }}</el-descriptions-item>
              </el-descriptions>
            </el-col>
          </el-row>

          <el-divider content-position="left">工序进度</el-divider>
          <el-table :data="operations" border size="small" empty-text="暂无工序数据">
            <el-table-column prop="seq" label="工序" width="80" />
            <el-table-column prop="station" label="工位" width="120" />
            <el-table-column label="进度" width="200">
              <template #default="{ row }">
                <el-progress :percentage="row.pct || 0" :stroke-width="8" />
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" />
          </el-table>

          <el-divider content-position="left">最近报工流水</el-divider>
          <el-table :data="progressRows" border size="small" empty-text="暂无报工记录">
            <el-table-column prop="logged_at" label="时间" width="170" />
            <el-table-column prop="seq" label="工序" width="80" />
            <el-table-column prop="station" label="工位" width="120" />
            <el-table-column prop="good_qty" label="合格" width="90" />
            <el-table-column prop="bad_qty" label="不良" width="90" />
            <el-table-column prop="operator" label="操作人" width="110" />
            <el-table-column prop="note" label="备注" />
          </el-table>
        </el-card>
      </template>

      <!-- ================= Tab 3: 工序报工 ================= -->
      <template v-else-if="activeTab === 'report'">
        <el-row :gutter="14">
          <el-col :span="10">
            <el-card class="sec">
              <template #header><span class="sec-title">📋 选择工单</span></template>
              <el-input v-model="searchWo" placeholder="搜索工单号/产品编码" clearable style="margin-bottom:10px" />
              <div class="wo-scroll">
                <div
                  v-for="row in wipRows.filter(r => !searchWo || r.wo_no.includes(searchWo) || r.product_code.includes(searchWo))"
                  :key="row.id"
                  class="wo-item"
                  :class="{ selected: currentWo?.id === row.id }"
                  @click="selectWo(row)"
                >
                  <div class="wo-item-top">
                    <span class="wo-item-no">{{ row.wo_no }}</span>
                    <el-tag size="small" :type="statusTag(row.status).type" effect="plain">{{ statusTag(row.status).text }}</el-tag>
                  </div>
                  <div class="wo-item-prod">{{ row.product_code }} · {{ row.station || '-' }}</div>
                  <el-progress
                    :percentage="row.plan_qty ? Math.round(row.done_qty / row.plan_qty * 100) : 0"
                    :stroke-width="6"
                    :color="rateColor(row.plan_qty ? row.done_qty / row.plan_qty * 100 : 0)"
                  />
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="14">
            <template v-if="currentWo">
              <el-card class="sec">
                <template #header>
                  <div class="sec-head">
                    <span class="sec-title">📥 工序报工 · {{ currentWo.wo_no }}</span>
                    <el-tag size="small">剩余 {{ (Number(currentWo.plan_qty) - Number(currentWo.done_qty)).toFixed(0) }} 台</el-tag>
                  </div>
                </template>
                <el-form label-width="100px" class="report-form">
                  <el-form-item label="工序序号">
                    <el-input-number v-model="reportForm.seq" :min="1" :max="99" />
                  </el-form-item>
                  <el-form-item label="本次合格数">
                    <el-input-number v-model="reportForm.good_qty" :min="0" :precision="3" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="本次不良数">
                    <el-input-number v-model="reportForm.bad_qty" :min="0" :precision="3" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="工位">
                    <el-input v-model="reportForm.station" :placeholder="currentWo.station" />
                  </el-form-item>
                  <el-form-item label="备注">
                    <el-input v-model="reportForm.note" type="textarea" :rows="2" />
                  </el-form-item>
                  <el-form-item label="幂等键">
                    <el-input v-model="reportForm.idempotency_key" placeholder="可选，防止重复提交" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="reporting" @click="submitReport">确认报工</el-button>
                    <el-button @click="reportForm = { seq: 1, good_qty: 0, bad_qty: 0, station: '', note: '', idempotency_key: '' }">重置</el-button>
                  </el-form-item>
                </el-form>
              </el-card>

              <el-card class="sec" style="margin-top:14px">
                <template #header><span class="sec-title">📜 最近报工流水</span></template>
                <el-table :data="progressRows" border size="small" empty-text="暂无报工记录">
                  <el-table-column prop="logged_at" label="时间" width="170" />
                  <el-table-column prop="seq" label="工序" width="80" />
                  <el-table-column prop="station" label="工位" width="120" />
                  <el-table-column label="合格" width="90">
                    <template #default="{ row }"><span style="color:#22c55e;font-weight:600">+{{ row.good_qty }}</span></template>
                  </el-table-column>
                  <el-table-column label="不良" width="90">
                    <template #default="{ row }" v-if="Number(row.bad_qty) > 0"><span style="color:#f56c6c">{{ row.bad_qty }}</span></template>
                    <template #default="{ row }" v-else>-</template>
                  </el-table-column>
                  <el-table-column prop="operator" label="操作人" width="110" />
                  <el-table-column prop="note" label="备注" />
                </el-table>
              </el-card>
            </template>
            <el-empty v-else description="← 请先从左侧选择一张在制工单" />
          </el-col>
        </el-row>
      </template>

      <!-- ================= Tab 4: 龄分析 ================= -->
      <template v-else-if="activeTab === 'aging'">
        <el-row :gutter="14">
          <el-col :span="8">
            <el-card class="sec">
              <template #header><span class="sec-title">⏱️ 龄分布（小时）</span></template>
              <div v-for="b in agingBuckets" :key="b.label" class="age-bar-row">
                <div class="age-bar-lbl">{{ b.label }}</div>
                <div class="age-bar-track">
                  <div class="age-bar-fill" :style="{ width: `${(b.count / Math.max(...agingBuckets.map(x => x.count), 1)) * 100}%`, background: b.label === '>72h' ? '#ef4444' : b.label === '48-72h' ? '#f59e0b' : b.label === '24-48h' ? '#eab308' : '#22c55e' }"></div>
                </div>
                <div class="age-bar-val">{{ b.count }}</div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="16">
            <el-card class="sec">
              <template #header>
                <div class="sec-head">
                  <span class="sec-title">🔥 超龄工单明细</span>
                  <el-tag type="danger" size="small" effect="dark">超过 24h 共 {{ (summary?.aging_wips || []).length }} 单</el-tag>
                </div>
              </template>
              <el-table :data="summary?.aging_wips || []" border stripe size="small" empty-text="无超龄工单">
                <el-table-column prop="wo_no" label="工单号" width="160" />
                <el-table-column label="产品" width="180">
                  <template #default="{ row }">{{ row.product_name || row.product_code }}</template>
                </el-table-column>
                <el-table-column prop="station" label="工位" width="100">
                  <template #default="{ row }"><el-tag size="small">{{ row.station || '-' }}</el-tag></template>
                </el-table-column>
                <el-table-column label="剩余台数" width="110">
                  <template #default="{ row }"><b style="color:#f59e0b">{{ row.wip_qty.toFixed(1) }}</b></template>
                </el-table-column>
                <el-table-column label="龄(h)" width="110" sortable>
                  <template #default="{ row }">
                    <span :style="{ color: row.aging_hours > 72 ? '#ef4444' : row.aging_hours > 48 ? '#f59e0b' : '#eab308', fontWeight: 700 }">
                      {{ row.aging_hours }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }"><el-tag size="small" :type="statusTag(row.status).type">{{ statusTag(row.status).text }}</el-tag></template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </template>

    </div>
  </div>
</template>

<style scoped>
.hub-header { padding: 16px 20px; background: linear-gradient(135deg, #f0fff4 0%, #ffffff 100%); border: 1px solid #d4f0e0; border-radius: 10px 10px 0 0; border-bottom: none; }
.hub-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.hub-title { font-size: 20px; font-weight: 700; color: #1a2b4a; }
.hub-tag { font-size: 12px; }
.hub-sub { font-size: 13px; color: #7a8da5; }
.hub-tabs { background: #fff; padding: 0 16px; border: 1px solid #d4f0e0; border-top: none; border-bottom: none; }
.hub-tabs :deep(.el-tabs__nav-wrap::after) { background-color: #d4f0e0; }
.hub-tabs :deep(.el-tabs__item) { height: 42px; line-height: 42px; font-size: 14px; padding: 0 16px; color: #455671; font-weight: 500; }
.hub-tabs :deep(.el-tabs__item.is-active) { color: #22c55e; font-weight: 600; }
.hub-tabs :deep(.el-tabs__active-bar) { background-color: #22c55e; height: 3px; border-radius: 2px; }
.hub-content { background: #fff; border: 1px solid #d4f0e0; border-top: none; border-radius: 0 0 10px 10px; padding: 16px; min-height: calc(100vh - 240px); }

.kpi-row { margin-bottom: 14px; }
.kpi-card { display: flex; align-items: center; gap: 12px; padding: 14px; border-radius: 10px; background: #fff; border: 1px solid #e2ecff; height: 92px; }
.kpi-icon { font-size: 26px; line-height: 1; }
.kpi-content { flex: 1; min-width: 0; }
.kpi-label { font-size: 12px; color: #7a8da5; margin-bottom: 4px; }
.kpi-value { font-size: 24px; font-weight: 700; color: #1a2b4a; line-height: 1.1; }
.kpi-value.small { font-size: 18px; }
.kpi-sub { font-size: 12px; color: #7a8da5; margin-top: 3px; }
.unit { font-size: 12px; font-weight: 400; color: #7a8da5; margin-left: 2px; }
.kpi-blue { border-left: 3px solid #2b7cff; }
.kpi-cyan { border-left: 3px solid #06b6d4; }
.kpi-green { border-left: 3px solid #22c55e; }
.kpi-orange { border-left: 3px solid #f59e0b; }
.kpi-red { border-left: 3px solid #ef4444; }
.kpi-purple { border-left: 3px solid #8b5cf6; }

.sec { margin-bottom: 14px; border-radius: 10px; }
.sec-head { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.sec-title { font-weight: 600; font-size: 14px; color: #1a2b4a; }
.empty { text-align: center; padding: 40px 0; color: #999; font-size: 13px; }
.empty.green { color: #22c55e; }

.s-row { margin-bottom: 12px; }
.s-row:last-child { margin-bottom: 0; }
.s-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.s-name { font-weight: 600; color: #1a2b4a; font-size: 14px; }
.s-meta { display: flex; gap: 10px; font-size: 12px; color: #7a8da5; align-items: center; }
.s-meta b { color: #2b7cff; }
.s-bar { position: relative; height: 22px; background: #eef3fd; border-radius: 6px; overflow: hidden; }
.s-fill { height: 100%; border-radius: 6px; min-width: 2px; }
.s-lbl { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-size: 11px; color: #1a2b4a; font-weight: 600; }

.age-item { display: flex; gap: 10px; padding: 10px 8px; border-radius: 8px; margin-bottom: 8px; background: #fafbfe; border-left: 3px solid #e2ecff; }
.age-item:last-child { margin-bottom: 0; }
.age-l { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.age-l.danger { background: #fee2e2; }
.age-l.warning { background: #fef3c7; }
.age-l.info { background: #e0f2fe; }
.age-b { flex: 1; min-width: 0; }
.age-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.age-wo { font-family: 'Consolas', monospace; font-weight: 600; color: #1a2b4a; font-size: 13px; }
.age-prod { font-size: 13px; color: #455671; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.age-meta { font-size: 12px; color: #7a8da5; margin-top: 2px; }
.age-meta b { color: #455671; }

.ledger-toolbar { margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
.link { color: #2b7cff; font-weight: 600; font-family: 'Consolas', monospace; cursor: pointer; }
.link:hover { text-decoration: underline; }
.sub { font-size: 12px; color: #7a8da5; line-height: 1.4; }
.sub.muted { color: #aab8c8; }
.qty-line { display: flex; gap: 10px; margin-bottom: 6px; font-size: 12px; }
.qty-p { color: #455671; }
.qty-d { color: #22c55e; }
.qty-w { color: #f59e0b; }
.qty-w b { font-size: 14px; }

.detail-card { margin-top: 14px; }

.wo-scroll { max-height: 500px; overflow-y: auto; }
.wo-item { padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; background: #fafbfe; border: 1px solid transparent; cursor: pointer; transition: all 0.15s; }
.wo-item:hover { background: #f0f6ff; border-color: #c5d9ff; }
.wo-item.selected { background: #e6f4ea; border-color: #22c55e; }
.wo-item-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.wo-item-no { font-family: 'Consolas', monospace; font-weight: 600; color: #1a2b4a; font-size: 13px; }
.wo-item-prod { font-size: 12px; color: #7a8da5; margin-bottom: 6px; }

.report-form { max-width: 480px; }

.age-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.age-bar-row:last-child { margin-bottom: 0; }
.age-bar-lbl { width: 60px; font-size: 12px; color: #455671; font-weight: 600; }
.age-bar-track { flex: 1; height: 18px; background: #eef3fd; border-radius: 4px; overflow: hidden; }
.age-bar-fill { height: 100%; border-radius: 4px; min-width: 2px; transition: width 0.3s; }
.age-bar-val { width: 30px; font-size: 13px; font-weight: 700; color: #1a2b4a; text-align: right; }
</style>
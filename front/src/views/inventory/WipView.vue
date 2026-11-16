<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { wipSummary, listWorkOrders, transitionWo } from '@/api/production'

const loading = ref(false)
const summary = ref(null)
const detailLoading = ref(false)
const wipRows = ref([])

const WIP_STATUSES = ['RELEASED', 'RUNNING']

async function loadAll() {
  loading.value = true
  try {
    const [s, wo] = await Promise.all([
      wipSummary().catch(() => null),
      listWorkOrders({ size: 200 }).catch(() => null),
    ])
    summary.value = s
    wipRows.value = (wo?.items || []).filter(r => WIP_STATUSES.includes(r.status))
  } catch (e) {
    ElMessage.error('WIP 数据加载失败: ' + (e?.message || e))
  } finally { loading.value = false }
}

function rateColor(r) {
  if (r >= 80) return '#22c55e'
  if (r >= 50) return '#2b7cff'
  if (r >= 20) return '#eab308'
  return '#f56c6c'
}

function statusTag(s) {
  const map = {
    PLANNED: { text: '待下达', type: 'info' },
    RELEASED: { text: '已下达', type: 'primary' },
    RUNNING: { text: '生产中', type: 'success' },
    DONE: { text: '已完工', type: 'success' },
    SCRAPPED: { text: '已报废', type: 'danger' },
  }
  return map[s] || { text: s, type: 'info' }
}

async function quickReport(row) {
  ElMessage.info(`进入报工页面 (WO-${row.wo_no})`)
}

async function quickFinish(row) {
  try {
    await transitionWo(row.id, 'DONE')
    ElMessage.success(`${row.wo_no} 已标记完工`)
    await loadAll()
  } catch (e) {
    ElMessage.error('状态流转失败: ' + (e?.message || e))
  }
}

const maxStationWip = computed(() => {
  const arr = summary.value?.stations || []
  return arr.length ? Math.max(...arr.map(s => s.wip_qty)) : 1
})

const severityClass = (h) => {
  if (h > 72) return 'danger'
  if (h > 48) return 'warning'
  return 'info'
}

onMounted(loadAll)
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="4">
        <div class="kpi-card kpi-blue">
          <div class="kpi-icon">📦</div>
          <div class="kpi-content">
            <div class="kpi-label">在制工单</div>
            <div class="kpi-value">{{ summary?.total_wip_wo ?? 0 }}<span class="unit">张</span></div>
          </div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="kpi-card kpi-cyan">
          <div class="kpi-icon">🔄</div>
          <div class="kpi-content">
            <div class="kpi-label">在制数量</div>
            <div class="kpi-value">{{ (summary?.wip_qty ?? 0).toFixed(2) }}<span class="unit">台</span></div>
          </div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="kpi-card kpi-green">
          <div class="kpi-icon">✅</div>
          <div class="kpi-content">
            <div class="kpi-label">平均完工率</div>
            <div class="kpi-value">{{ summary?.avg_done_rate ?? 0 }}<span class="unit">%</span></div>
          </div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="kpi-card kpi-orange">
          <div class="kpi-icon">⚠️</div>
          <div class="kpi-content">
            <div class="kpi-label">瓶颈工位</div>
            <div class="kpi-value small">
              {{ summary?.bottleneck_station || '-' }}
            </div>
            <div class="kpi-sub">在制 {{ (summary?.bottleneck_wip_qty ?? 0).toFixed(0) }} 台</div>
          </div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="kpi-card kpi-red">
          <div class="kpi-icon">⏰</div>
          <div class="kpi-content">
            <div class="kpi-label">超龄预警</div>
            <div class="kpi-value">{{ summary?.overdue_wip_count ?? 0 }}<span class="unit">单</span></div>
            <div class="kpi-sub">超过 24h 未完工</div>
          </div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="kpi-card kpi-purple">
          <div class="kpi-icon">🏭</div>
          <div class="kpi-content">
            <div class="kpi-label">覆盖工位</div>
            <div class="kpi-value">{{ summary?.stations?.length ?? 0 }}<span class="unit">个</span></div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mid-row">
      <el-col :span="15">
        <el-card class="section-card">
          <template #header>
            <div class="section-head">
              <span class="section-title">工位 WIP 分布</span>
              <div class="section-tools">
                <el-tag size="small" effect="plain">按在制量排序</el-tag>
                <el-button size="small" text @click="loadAll">刷新</el-button>
              </div>
            </div>
          </template>
          <div v-if="!summary?.stations?.length" class="empty-tip">暂无在制品数据</div>
          <div v-for="s in (summary?.stations || [])" :key="s.station" class="station-row">
            <div class="station-head">
              <span class="station-name">{{ s.station }}</span>
              <span class="station-meta">
                <el-tag size="small" effect="plain">{{ s.wo_count }} 工单</el-tag>
                <span class="meta-val">在制 <b>{{ s.wip_qty.toFixed(1) }}</b></span>
                <span class="meta-val">平均 <b>{{ s.avg_aging_hours }}h</b></span>
              </span>
            </div>
            <div class="station-bar">
              <div
                class="bar-fill"
                :style="{
                  width: `${(s.wip_qty / maxStationWip) * 100}%`,
                  background: `linear-gradient(90deg, ${rateColor(s.done_rate)}, ${rateColor(s.done_rate)}aa)`,
                }"
              ></div>
              <span class="bar-label">完工率 {{ s.done_rate }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="9">
        <el-card class="section-card">
          <template #header>
            <div class="section-head">
              <span class="section-title">⚠️ 超龄预警（>24h）</span>
              <el-tag v-if="summary?.overdue_wip_count" type="danger" size="small" effect="dark">
                {{ summary.overdue_wip_count }} 项
              </el-tag>
            </div>
          </template>
          <div v-if="!summary?.aging_wips?.length" class="empty-tip green">✓ 全部在制品龄正常</div>
          <div v-for="w in (summary?.aging_wips || [])" :key="w.wo_id" class="aging-item">
            <div class="aging-left" :class="severityClass(w.aging_hours)">
              {{ w.aging_hours > 72 ? '🔥' : w.aging_hours > 48 ? '⚠️' : '⏰' }}
            </div>
            <div class="aging-body">
              <div class="aging-top">
                <span class="aging-wo">{{ w.wo_no }}</span>
                <el-tag size="small" :type="statusTag(w.status).type" effect="plain">{{ statusTag(w.status).text }}</el-tag>
              </div>
              <div class="aging-product">{{ w.product_name || w.product_code }}</div>
              <div class="aging-meta">
                工位 <b>{{ w.station || '-' }}</b> · 剩余 <b>{{ w.wip_qty.toFixed(1) }}</b> 台 ·
                <span :style="{ color: w.aging_hours > 48 ? '#f56c6c' : '#eab308', fontWeight: 600 }">
                  已 {{ w.aging_hours }}h
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="section-card detail-card">
      <template #header>
        <div class="section-head">
          <span class="section-title">WIP 明细台账（生产中工单）</span>
          <div class="section-tools">
            <el-tag size="small" effect="plain">共 {{ wipRows.length }} 条</el-tag>
            <el-button size="small" text @click="loadAll">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="wipRows" border stripe v-loading="detailLoading">
        <el-table-column prop="wo_no" label="工单号" width="170" fixed="left">
          <template #default="{ row }">
            <span class="wo-link">{{ row.wo_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="product_code" label="产品" width="180">
          <template #default="{ row }">
            <div>{{ row.product_code }}</div>
            <div class="sub-text">{{ row.product_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="station" label="工位" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.station || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计划 / 完工 / 在制" width="260">
          <template #default="{ row }">
            <div class="qty-row">
              <span class="qty-plan">计划 {{ Number(row.plan_qty).toFixed(0) }}</span>
              <span class="qty-done">完工 {{ Number(row.done_qty).toFixed(0) }}</span>
              <span class="qty-wip">在制 <b>{{ (Number(row.plan_qty) - Number(row.done_qty)).toFixed(0) }}</b></span>
            </div>
            <el-progress
              :percentage="row.plan_qty ? Math.round(row.done_qty / row.plan_qty * 100) : 0"
              :stroke-width="10"
              :color="rateColor(row.plan_qty ? row.done_qty / row.plan_qty * 100 : 0)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status).type" effect="dark">{{ statusTag(row.status).text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计划时间" width="220">
          <template #default="{ row }">
            <div class="sub-text">{{ row.planned_start?.slice(0, 16) || '-' }}</div>
            <div class="sub-text muted">→ {{ row.planned_end?.slice(0, 16) || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="quickReport(row)">报工</el-button>
            <el-button size="small" type="success" link @click="quickFinish(row)">完工</el-button>
            <el-button size="small" link>详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.kpi-row { margin-bottom: 16px; }
.mid-row { margin-bottom: 16px; }

.kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffffff 0%, #f5f8ff 100%);
  border: 1px solid #e2ecff;
  box-shadow: 0 2px 8px rgba(43, 124, 255, 0.06);
  height: 96px;
}
.kpi-icon { font-size: 28px; line-height: 1; }
.kpi-content { flex: 1; min-width: 0; }
.kpi-label { font-size: 12px; color: #7a8da5; margin-bottom: 4px; }
.kpi-value { font-size: 26px; font-weight: 700; line-height: 1.1; color: #1a2b4a; }
.kpi-value.small { font-size: 20px; }
.kpi-sub { font-size: 12px; color: #7a8da5; margin-top: 4px; }
.unit { font-size: 13px; font-weight: 400; color: #7a8da5; margin-left: 2px; }

.kpi-blue { border-left: 3px solid #2b7cff; }
.kpi-cyan { border-left: 3px solid #06b6d4; }
.kpi-green { border-left: 3px solid #22c55e; }
.kpi-orange { border-left: 3px solid #f59e0b; }
.kpi-red { border-left: 3px solid #ef4444; background: linear-gradient(135deg, #fff5f5 0%, #fff 100%); }
.kpi-purple { border-left: 3px solid #8b5cf6; }

.section-card { border-radius: 10px; }
.section-head { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.section-title { font-weight: 600; font-size: 15px; color: #1a2b4a; }
.section-tools { display: flex; align-items: center; gap: 8px; }

.empty-tip { text-align: center; padding: 40px 0; color: #999; font-size: 13px; }
.empty-tip.green { color: #22c55e; }

.station-row { margin-bottom: 14px; }
.station-row:last-child { margin-bottom: 0; }
.station-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.station-name { font-weight: 600; color: #1a2b4a; font-size: 14px; }
.station-meta { display: flex; align-items: center; gap: 10px; font-size: 12px; color: #7a8da5; }
.station-meta .meta-val b { color: #2b7cff; }
.station-bar {
  position: relative;
  height: 22px;
  background: #eef3fd;
  border-radius: 6px;
  overflow: hidden;
}
.bar-fill { height: 100%; border-radius: 6px; transition: width 0.4s ease; min-width: 2px; }
.bar-label {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: #1a2b4a;
  font-weight: 600;
}

.aging-item {
  display: flex;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 8px;
  margin-bottom: 8px;
  background: #fafbfe;
  border-left: 3px solid #e2ecff;
}
.aging-item:last-child { margin-bottom: 0; }
.aging-left {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.aging-left.danger { background: #fee2e2; }
.aging-left.warning { background: #fef3c7; }
.aging-left.info { background: #e0f2fe; }
.aging-body { flex: 1; min-width: 0; }
.aging-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.aging-wo { font-family: 'Consolas', monospace; font-weight: 600; color: #1a2b4a; font-size: 13px; }
.aging-product { font-size: 13px; color: #455671; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aging-meta { font-size: 12px; color: #7a8da5; margin-top: 2px; }
.aging-meta b { color: #455671; }

.detail-card :deep(.el-table) { font-size: 13px; }
.wo-link { color: #2b7cff; font-weight: 600; font-family: 'Consolas', monospace; cursor: pointer; }
.wo-link:hover { text-decoration: underline; }
.sub-text { font-size: 12px; color: #7a8da5; line-height: 1.4; }
.sub-text.muted { color: #aab8c8; }
.qty-row { display: flex; gap: 10px; margin-bottom: 6px; font-size: 12px; }
.qty-plan { color: #455671; }
.qty-done { color: #22c55e; }
.qty-wip { color: #f59e0b; }
.qty-wip b { font-size: 14px; }
</style>
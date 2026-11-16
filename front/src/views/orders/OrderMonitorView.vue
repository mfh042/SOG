<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listOrders, releaseOrder, transitionOrder, splitOrder } from '@/api/orders'

const rows = ref([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')

const statusMap = {
  DRAFT: { text: '草稿', type: 'info' },
  RELEASED: { text: '已下达', type: 'primary' },
  IN_PROGRESS: { text: '生产中', type: 'warning' },
  COMPLETED: { text: '已完工', type: 'success' },
  CLOSED: { text: '已关闭', type: 'info' },
  CANCELLED: { text: '已取消', type: 'danger' },
  LOCKED: { text: '已锁定', type: 'danger' },
}

async function load() {
  loading.value = true
  try {
    const data = await listOrders({ size: 200 })
    rows.value = data?.items || []
  } catch (e) {
    ElMessage.error('加载订单失败: ' + (e?.message || e))
  } finally { loading.value = false }
}

const filteredRows = computed(() => {
  return rows.value.filter(r => {
    if (statusFilter.value && r.status !== statusFilter.value) return false
    if (keyword.value) {
      const kw = keyword.value.toLowerCase()
      return (
        (r.order_no || '').toLowerCase().includes(kw) ||
        (r.customer_name || '').toLowerCase().includes(kw) ||
        (r.product_model || '').toLowerCase().includes(kw) ||
        (r.product_name || '').toLowerCase().includes(kw)
      )
    }
    return true
  })
})

const totalQty = computed(() => rows.value.reduce((s, r) => s + Number(r.qty || 0), 0))
const releasedCount = computed(() => rows.value.filter(r => r.status === 'RELEASED').length)
const inProgressCount = computed(() => rows.value.filter(r => r.status === 'IN_PROGRESS').length)
const completedCount = computed(() => rows.value.filter(r => r.status === 'COMPLETED').length)

const statusBuckets = computed(() => {
  const orders = rows.value
  return [
    { label: '草稿', key: 'DRAFT', count: orders.filter(r => r.status === 'DRAFT').length, color: '#909399' },
    { label: '已下达', key: 'RELEASED', count: orders.filter(r => r.status === 'RELEASED').length, color: '#2b7cff' },
    { label: '生产中', key: 'IN_PROGRESS', count: orders.filter(r => r.status === 'IN_PROGRESS').length, color: '#eab308' },
    { label: '已完工', key: 'COMPLETED', count: orders.filter(r => r.status === 'COMPLETED').length, color: '#22c55e' },
    { label: '已关闭', key: 'CLOSED', count: orders.filter(r => r.status === 'CLOSED').length, color: '#aab8c8' },
    { label: '已取消', key: 'CANCELLED', count: orders.filter(r => r.status === 'CANCELLED').length, color: '#ef4444' },
  ]
})

const statusChartMax = computed(() => Math.max(...statusBuckets.value.map(b => b.count), 1))

const todayStr = new Date().toISOString().slice(0, 10)
const overdueCount = computed(() =>
  rows.value.filter(r =>
    ['RELEASED', 'IN_PROGRESS'].includes(r.status) &&
    r.planned_date && r.planned_date < todayStr
  ).length
)

async function doRelease(row) {
  try {
    await releaseOrder(row.id)
    ElMessage.success(`${row.order_no} 已下达`)
    await load()
  } catch (e) {
    ElMessage.error('下达失败: ' + (e?.message || e))
  }
}

async function doTransition(row, target) {
  try {
    await transitionOrder(row.id, target)
    ElMessage.success(`${row.order_no} → ${target}`)
    await load()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e?.message || e))
  }
}

const priorityMap = { 1: { text: '特急', type: 'danger' }, 2: { text: '高', type: 'warning' }, 3: { text: '中', type: '' }, 4: { text: '低', type: 'info' } }

onMounted(load)
</script>

<template>
  <div class="monitor" v-loading="loading">
    <div class="page-header">
      <div class="title-row">
        <span class="page-title">📋 生产订单监控</span>
        <el-tag type="primary" effect="dark">全部 {{ rows.length }} 单</el-tag>
      </div>
      <div class="page-sub">订单全生命周期状态追踪 · 下达 · 生产 · 完工</div>
    </div>

    <el-row :gutter="14" class="kpi-row">
      <el-col :span="4" v-for="k in [
        { icon: '📦', label: '总订单数', val: rows.length, unit: '单', cls: 'kpi-blue', sub: `总数量 ${totalQty} 台` },
        { icon: '📤', label: '已下达', val: releasedCount, unit: '单', cls: 'kpi-cyan' },
        { icon: '🔄', label: '生产中', val: inProgressCount, unit: '单', cls: 'kpi-orange' },
        { icon: '✅', label: '已完工', val: completedCount, unit: '单', cls: 'kpi-green' },
        { icon: '⚠️', label: '逾期订单', val: overdueCount, unit: '单', cls: 'kpi-red', sub: '计划日期已过' },
        { icon: '📊', label: '完工率', val: rows.length ? Math.round(completedCount / rows.length * 100) : 0, unit: '%', cls: 'kpi-purple' },
      ]" :key="k.label">
        <div class="kpi-card" :class="k.cls">
          <div class="kpi-icon">{{ k.icon }}</div>
          <div class="kpi-content">
            <div class="kpi-label">{{ k.label }}</div>
            <div class="kpi-value">{{ k.val }}<span class="unit">{{ k.unit }}</span></div>
            <div class="kpi-sub" v-if="k.sub">{{ k.sub }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="14">
      <el-col :span="8">
        <el-card class="sec">
          <template #header><span class="sec-title">📊 状态分布</span></template>
          <div v-for="b in statusBuckets" :key="b.key" class="bar-row">
            <div class="bar-lbl">
              <el-tag size="small" :type="statusMap[b.key]?.type || 'info'" effect="plain">{{ b.label }}</el-tag>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: `${(b.count / statusChartMax) * 100}%`, background: b.color }"></div>
            </div>
            <div class="bar-val">{{ b.count }}</div>
          </div>
        </el-card>

        <el-card class="sec" style="margin-top:14px">
          <template #header><span class="sec-title">🎯 高优先级订单</span></template>
          <div v-if="!rows.filter(r => r.priority && r.priority <= 2 && ['RELEASED','IN_PROGRESS'].includes(r.status)).length" class="empty">暂无紧急订单</div>
          <div
            v-for="r in rows.filter(r => r.priority && r.priority <= 2 && ['RELEASED','IN_PROGRESS'].includes(r.status)).slice(0, 8)"
            :key="r.id"
            class="urgent-item"
          >
            <div class="urgent-l">
              <span class="urgent-no">{{ r.order_no }}</span>
              <el-tag size="small" :type="priorityMap[r.priority]?.type" effect="dark">{{ priorityMap[r.priority]?.text || 'P' }}优先级</el-tag>
            </div>
            <div class="urgent-m">
              {{ r.product_model || r.product_name }} · {{ r.qty }}台
            </div>
            <div class="urgent-r">
              <el-tag size="small" :type="statusMap[r.status]?.type">{{ statusMap[r.status]?.text }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card class="sec">
          <template #header>
            <div class="sec-head">
              <span class="sec-title">📋 订单列表（{{ filteredRows.length }} / {{ rows.length }}）</span>
              <div class="filter-bar">
                <el-input v-model="keyword" placeholder="订单号/客户/产品" clearable size="small" style="width:200px;margin-right:8px" />
                <el-select v-model="statusFilter" placeholder="状态" clearable size="small" style="width:120px;margin-right:8px">
                  <el-option v-for="(v, k) in statusMap" :key="k" :label="v.text" :value="k" />
                </el-select>
                <el-button size="small" @click="load">🔄 刷新</el-button>
              </div>
            </div>
          </template>

          <el-table :data="filteredRows" border stripe size="small">
            <el-table-column prop="order_no" label="订单号" width="170" fixed="left">
              <template #default="{ row }"><span class="link">{{ row.order_no }}</span></template>
            </el-table-column>
            <el-table-column prop="customer_name" label="客户" width="120" show-overflow-tooltip />
            <el-table-column label="产品" width="170">
              <template #default="{ row }">
                <div>{{ row.product_model || '-' }}</div>
                <div class="sub muted">{{ row.product_name }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="qty" label="数量" width="80" align="right">
              <template #default="{ row }"><b>{{ Number(row.qty).toFixed(0) }}</b></template>
            </el-table-column>
            <el-table-column label="优先级" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.priority" size="small" :type="priorityMap[row.priority]?.type" effect="plain">{{ priorityMap[row.priority]?.text }}</el-tag>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="statusMap[row.status]?.type" effect="dark">{{ statusMap[row.status]?.text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="planned_date" label="计划日期" width="120" align="center">
              <template #default="{ row }">
                <span :class="{ overdue: row.planned_date && ['RELEASED','IN_PROGRESS'].includes(row.status) && row.planned_date < todayStr }">
                  {{ row.planned_date || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{ row }"><span class="sub muted">{{ row.created_at?.slice(0, 16) }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'DRAFT'" size="small" type="primary" link @click="doRelease(row)">下达</el-button>
                <el-button v-if="row.status === 'RELEASED'" size="small" type="warning" link @click="doTransition(row, 'IN_PROGRESS')">投产</el-button>
                <el-button v-if="row.status === 'IN_PROGRESS'" size="small" type="success" link @click="doTransition(row, 'COMPLETED')">完工</el-button>
                <el-button v-if="row.status === 'COMPLETED'" size="small" type="info" link @click="doTransition(row, 'CLOSED')">关闭</el-button>
                <el-button size="small" link detail-btn>详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.page-header { padding: 16px 20px; background: linear-gradient(135deg, #f0f6ff 0%, #ffffff 100%); border: 1px solid #e2ecff; border-radius: 10px 10px 0 0; border-bottom: none; }
.title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.page-title { font-size: 20px; font-weight: 700; color: #1a2b4a; }
.page-sub { font-size: 13px; color: #7a8da5; }
.kpi-row { margin-bottom: 14px; margin-top: 0; padding-top: 14px; }
.kpi-card { display: flex; align-items: center; gap: 12px; padding: 14px; border-radius: 10px; background: #fff; border: 1px solid #e2ecff; height: 92px; }
.kpi-icon { font-size: 26px; line-height: 1; }
.kpi-content { flex: 1; min-width: 0; }
.kpi-label { font-size: 12px; color: #7a8da5; margin-bottom: 4px; }
.kpi-value { font-size: 24px; font-weight: 700; color: #1a2b4a; line-height: 1.1; }
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
.filter-bar { display: flex; align-items: center; }
.empty { text-align: center; padding: 40px 0; color: #999; font-size: 13px; }

.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-lbl { width: 64px; flex-shrink: 0; }
.bar-track { flex: 1; height: 20px; background: #eef3fd; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; min-width: 2px; transition: width 0.3s; }
.bar-val { width: 28px; font-size: 14px; font-weight: 700; color: #1a2b4a; text-align: right; }

.urgent-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; background: #fff7ed; border-left: 3px solid #f59e0b; }
.urgent-item:last-child { margin-bottom: 0; }
.urgent-l { flex-shrink: 0; }
.urgent-no { font-family: 'Consolas', monospace; font-weight: 600; color: #1a2b4a; font-size: 13px; display: block; margin-bottom: 3px; }
.urgent-m { flex: 1; font-size: 12px; color: #455671; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.urgent-r { flex-shrink: 0; }

.link { color: #2b7cff; font-weight: 600; font-family: 'Consolas', monospace; cursor: pointer; }
.link:hover { text-decoration: underline; }
.sub { font-size: 12px; line-height: 1.4; }
.sub.muted { color: #aab8c8; }
.muted { color: #aab8c8; }
.overdue { color: #ef4444; font-weight: 600; }
.detail-btn { font-size: 12px !important; }
</style>
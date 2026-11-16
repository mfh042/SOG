<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listOrders, transitionOrder, releaseOrder,
  splitOrder as splitOrderApi, rescheduleOrder, adjustQtyOrder, batchReleaseOrders,
} from '@/api/orders'

const rows = ref([])
const loading = ref(false)
const selected = ref([])

const statusMap = {
  DRAFT: '草稿', RELEASED: '已下达', IN_PROGRESS: '生产中',
  COMPLETED: '已完工', CLOSED: '已关闭', CANCELLED: '已取消', LOCKED: '已锁定',
}
const statusTagType = {
  DRAFT: 'info', RELEASED: 'primary', IN_PROGRESS: 'warning',
  COMPLETED: 'success', CLOSED: 'info', CANCELLED: 'danger', LOCKED: 'danger',
}

async function load() {
  loading.value = true
  try {
    const data = await listOrders({ size: 200 })
    rows.value = data?.items || []
  } finally { loading.value = false }
}

async function handleSplit(row) {
  const total = Number(row.qty) || 1
  const { value: num } = await ElMessageBox.prompt('请输入拆分数量（从前 N 台拆出新工单）', '订单拆分', {
    inputPattern: new RegExp(`^[1-9]\\d*$`),
    inputErrorMessage: `请输入 1 ~ ${total - 1} 之间的整数`,
    inputDefaultValue: Math.floor(total / 2),
  }).catch(() => ({ value: null }))
  if (!num) return
  try {
    await splitOrderApi(row.id, Number(num))
    ElMessage.success(`已从 ${row.order_no} 拆出 ${num} 台`)
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '拆分失败')
  }
}

async function handleReschedule(row) {
  const { value: date } = await ElMessageBox.prompt('请输入新的计划日期 YYYY-MM-DD', '订单排产', {
    inputDefaultValue: row.planned_date || new Date().toISOString().slice(0, 10),
  }).catch(() => ({ value: null }))
  if (!date) return
  try {
    await rescheduleOrder(row.id, date)
    ElMessage.success(`计划日期已更新为 ${date}`)
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '排产失败')
  }
}

async function handleAdjustQty(row) {
  const total = Number(row.qty) || 1
  const { value: qty } = await ElMessageBox.prompt(`当前数量 ${total}，请输入新数量`, '订单数量调整', {
    inputPattern: /^[1-9]\d*$/, inputErrorMessage: '请输入正整数', inputDefaultValue: total,
  }).catch(() => ({ value: null }))
  if (!qty) return
  try {
    await adjustQtyOrder(row.id, Number(qty))
    ElMessage.success('数量已更新')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '调整失败')
  }
}

async function lockToggle(row) {
  const target = row.status === 'LOCKED' ? 'DRAFT' : 'LOCKED'
  const action = target === 'LOCKED' ? '锁定' : '解锁'
  try {
    await ElMessageBox.confirm(`确认${action}订单 ${row.order_no}？`, '提示', { type: 'warning' })
    await transitionOrder(row.id, target)
    ElMessage.success(`已${action}`)
    load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function batchRelease() {
  const drafts = selected.value.filter(r => r.status === 'DRAFT')
  if (!drafts.length) return ElMessage.warning('请先选择草稿状态的工单')
  try {
    const res = await batchReleaseOrders(drafts.map(r => r.id))
    ElMessage.success(`批量完成：${res.data.ok} 成功，${res.data.fail} 失败`)
    selected.value = []
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '批量发布失败')
  }
}

async function batchLock() {
  const targets = selected.value.filter(r => r.status !== 'CANCELLED' && r.status !== 'CLOSED' && r.status !== 'LOCKED')
  if (!targets.length) return ElMessage.warning('无可锁定的工单')
  await ElMessageBox.confirm(`确认锁定 ${targets.length} 个工单？`, '提示', { type: 'warning' }).catch(() => { throw 'cancel' })
  let ok = 0
  for (const row of targets) {
    try { await transitionOrder(row.id, 'LOCKED'); ok++ } catch {}
  }
  ElMessage.success(`已锁定 ${ok} 个`)
  selected.value = []
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card action-bar">
      <div class="action-title">订单调整工作台</div>
      <div class="action-buttons">
        <el-button :disabled="!selected.length" @click="batchRelease">
          批量发布 <el-badge v-if="selected.length" :value="selected.length" class="badge" />
        </el-button>
        <el-button :disabled="!selected.length" plain type="warning" @click="batchLock">批量锁定</el-button>
        <el-button plain @click="load">刷新</el-button>
      </div>
    </div>

    <div class="card">
      <div class="hint">勾选订单后可批量操作；或点击行内按钮执行单项调整</div>
      <el-table v-loading="loading" :data="rows" stripe @selection-change="selected = $event">
        <el-table-column type="selection" width="46" />
        <el-table-column prop="order_no" label="工单编号" width="180" />
        <el-table-column prop="product_model" label="产品型号" min-width="130" />
        <el-table-column label="数量" width="80">
          <template #default="{ row }">{{ row.qty || row.items?.reduce((s, i) => s + Number(i.qty || 0), 0) }}</template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.priority >= 4 ? 'danger' : row.priority >= 3 ? 'warning' : 'info'">P{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType[row.status] || 'info'">{{ statusMap[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="planned_date" label="计划日期" width="120" />
        <el-table-column label="调整操作" width="420" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" :disabled="row.status === 'LOCKED' || row.status === 'CANCELLED'" @click="handleSplit(row)">拆分</el-button>
            <el-button size="small" link type="primary" :disabled="row.status === 'LOCKED' || row.status === 'CANCELLED'" @click="handleReschedule(row)">排产</el-button>
            <el-button size="small" link type="primary" :disabled="row.status === 'LOCKED' || row.status === 'CANCELLED' || row.status === 'COMPLETED'" @click="handleAdjustQty(row)">调数量</el-button>
            <el-button size="small" link type="warning" @click="lockToggle(row)">
              {{ row.status === 'LOCKED' ? '解锁' : '锁定' }}
            </el-button>
            <el-button v-if="row.status === 'DRAFT'" size="small" link type="success" @click="releaseOrder(row.id).then(()=>load())">发布</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 14px; }
.card { background: #fff; border-radius: 10px; padding: 16px 20px; border: 1px solid var(--border); }
.action-bar { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; }
.action-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.action-buttons { display: flex; gap: 10px; align-items: center; }
.hint { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
.badge { margin-left: 4px; }
</style>
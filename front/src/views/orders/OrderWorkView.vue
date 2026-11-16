<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Download, Plus, RefreshRight } from '@element-plus/icons-vue'
import { listOrders, createOrder, releaseOrder, transitionOrder, importOrders } from '@/api/orders'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const fileInput = ref(null)
const statusFilter = ref('')
const keyword = ref('')

const form = reactive({
  order_no: '', customer_name: '', product_model: '',
  priority: 3, planned_date: '', qty: 1, note: '',
})

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
    const data = await listOrders({ status: statusFilter.value || undefined, size: 200 })
    rows.value = data?.items || []
  } finally { loading.value = false }
}

async function submit() {
  try {
    await createOrder({ ...form, items: [{ material_code: form.product_model, material_name: form.product_model, qty: form.qty, unit: 'PCS' }] })
    ElMessage.success('生产工单已创建')
    dialog.value = false
    load()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
}

async function release(row) {
  try {
    const res = await releaseOrder(row.id)
    const woCount = res?.work_orders?.length || 0
    const warnCount = res?.warnings?.length || 0
    ElMessage.success(`已下达，生成 ${woCount} 张工单${warnCount ? `，${warnCount} 项缺料告警` : ''}`)
    load()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '下达失败') }
}

async function cancel(row) {
  try {
    await ElMessageBox.confirm('确认取消该生产工单？', '提示', { type: 'warning' })
    await transitionOrder(row.id, 'CANCELLED')
    ElMessage.success('已取消')
    load()
  } catch {}
}

function triggerImport() { fileInput.value?.click() }

async function handleImport(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const res = await importOrders(file)
    ElMessage.success(`导入完成：${res.data.created} 成功，${res.data.failed} 失败`)
    if (res.data.errors?.length) {
      ElMessage.warning(res.data.errors.slice(0, 3).map(x => `行${x.row}: ${x.error}`).join('；'))
    }
    load()
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '导入失败，请检查 CSV 格式')
  }
  e.target.value = ''
}

function handleExport() {
  ElMessage.info('演示：已生成 CSV 导出文件')
  const csv = '\uFEFF订单号,客户,产品型号,优先级,状态,计划日期\n' +
    rows.value.map(r => [r.order_no, r.customer_name, r.product_model, r.priority, statusMap[r.status], r.planned_date].join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `生产工单_${new Date().toISOString().slice(0,10)}.csv`; a.click()
  URL.revokeObjectURL(url)
}

function autoReceive() {
  ElMessage.success('演示：已从 ERP 接收 3 条新订单自动生成生产工单')
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input v-model="keyword" placeholder="订单号 / 产品 / 客户" clearable style="width: 220px" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px" @change="load">
          <el-option v-for="(v, k) in statusMap" :key="k" :label="v" :value="k" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button :icon="RefreshRight" plain @click="load">刷新</el-button>
        <el-button :icon="Download" plain @click="handleExport">导出</el-button>
        <el-button :icon="Upload" plain @click="triggerImport">导入</el-button>
        <input ref="fileInput" type="file" accept=".csv,.xlsx" style="display:none" @change="handleImport" />
        <el-button :icon="RefreshRight" @click="autoReceive" class="auto-btn">自动接收</el-button>
        <el-button type="primary" :icon="Plus" @click="dialog = true">手动新建</el-button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num">{{ rows.length }}</div>
        <div class="stat-label">全部</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ rows.filter(r => r.status === 'DRAFT').length }}</div>
        <div class="stat-label">草稿待下达</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ rows.filter(r => r.status === 'RELEASED' || r.status === 'IN_PROGRESS').length }}</div>
        <div class="stat-label">在制中</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ rows.filter(r => r.status === 'COMPLETED').length }}</div>
        <div class="stat-label">已完工</div>
      </div>
    </div>

    <div class="card">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="order_no" label="工单编号" width="180" />
        <el-table-column prop="customer_name" label="客户" min-width="120" />
        <el-table-column prop="product_model" label="产品型号" min-width="130" />
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
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'DRAFT'" size="small" type="primary" link @click="release(row)">下达</el-button>
            <el-button v-if="row.status !== 'CANCELLED' && row.status !== 'COMPLETED' && row.status !== 'CLOSED'" size="small" link type="danger" @click="cancel(row)">取消</el-button>
            <el-button size="small" link type="info">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog" title="手动编制生产工单" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户"><el-input v-model="form.customer_name" placeholder="客户名称" /></el-form-item>
        <el-form-item label="产品型号"><el-input v-model="form.product_model" placeholder="如 GB-100" /></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="form.qty" :min="1" :max="99999" style="width: 100%" /></el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="P1 紧急" :value="1" />
            <el-option label="P2 较高" :value="2" />
            <el-option label="P3 普通" :value="3" />
            <el-option label="P4 较低" :value="4" />
            <el-option label="P5 低" :value="5" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划日期"><el-date-picker v-model="form.planned_date" type="date" style="width: 100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 14px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.toolbar-left { display: flex; gap: 10px; }
.toolbar-right { display: flex; gap: 8px; }
.auto-btn { background: linear-gradient(135deg, #409eff, #2b7cff); border: none; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card {
  background: #fff; border-radius: 10px; padding: 14px 18px; border: 1px solid var(--border);
  display: flex; align-items: baseline; gap: 10px;
}
.stat-num { font-size: 26px; font-weight: 700; color: var(--brand); line-height: 1; }
.stat-label { font-size: 12px; color: var(--text-muted); }
.card { background: #fff; border-radius: 10px; padding: 16px 20px; border: 1px solid var(--border); }
</style>
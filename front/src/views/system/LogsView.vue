<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listAuditLogs, listAuditActions } from '@/api/auditLogs'

const rows = ref([])
const actions = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const size = ref(30)
const filter = reactive({
  action: '', target_type: '', actor_username: '', result: '',
})

const actionColors = {
  LOGIN: 'info', LOGOUT: 'info',
  DEFECT_CREATE: 'success', DEFECT_UPDATE: 'warning', DEFECT_DELETE: 'danger',
  INSPECT_TYPE_CREATE: 'success', INSPECT_TYPE_UPDATE: 'warning', INSPECT_TYPE_DELETE: 'danger',
  WO_CREATE: 'success', WO_UPDATE: 'warning', WO_RELEASE: 'primary', WO_TRANSITION: 'primary', WO_CANCEL: 'danger',
  PROD_REPORT: 'primary', PROD_TRANSITION: 'primary', PROD_SCRAP: 'danger',
  INSP_CREATE: 'success', INSP_UPDATE: 'warning',
  BOM_CREATE: 'success', BOM_UPDATE: 'warning',
  MATERIAL_CREATE: 'success', MATERIAL_UPDATE: 'warning',
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    if (filter.action) params.action = filter.action
    if (filter.target_type) params.target_type = filter.target_type
    if (filter.actor_username) params.actor_username = filter.actor_username
    if (filter.result) params.result = filter.result

    const res = await listAuditLogs(params)
    rows.value = res?.items || res?.data?.items || []
    total.value = res?.total || res?.data?.total || 0
  } catch (e) {
    ElMessage.error('加载失败: ' + (e?.message || e))
  } finally { loading.value = false }
}

async function loadActions() {
  try {
    const res = await listAuditActions()
    actions.value = res?.data || res || []
  } catch (e) { /* ignore */ }
}

function resetFilter() {
  Object.assign(filter, { action: '', target_type: '', actor_username: '', result: '' })
  page.value = 1
  load()
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(() => { load(); loadActions() })
</script>

<template>
  <div>
    <div class="card">
      <div class="card-title-row">
        <div class="card-title">审计日志</div>
        <el-tag type="success" size="small" effect="dark">共 {{ total }} 条</el-tag>
      </div>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="动作">
          <el-select v-model="filter.action" clearable placeholder="全部" style="width:200px">
            <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
          </el-select>
        </el-form-item>
        <el-form-item label="对象类型">
          <el-input v-model="filter.target_type" clearable placeholder="如 defect_code" style="width:160px" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="filter.actor_username" clearable placeholder="如 admin" style="width:140px" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="filter.result" clearable placeholder="全部" style="width:120px">
            <el-option label="SUCCESS" value="SUCCESS" />
            <el-option label="FAIL" value="FAIL" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="rows" border stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="action" label="动作" width="180">
          <template #default="{ row }">
            <el-tag size="small" :type="actionColors[row.action] || 'info'" effect="plain">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作对象" min-width="200">
          <template #default="{ row }">
            <span class="mono">{{ row.target_type }}:{{ row.target_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作人" width="160">
          <template #default="{ row }">
            <span class="mono">{{ row.actor_username || 'system' }}</span>
            <el-tag v-if="row.actor_role" size="small" style="margin-left:4px">{{ row.actor_role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.result === 'SUCCESS' ? 'success' : 'danger'">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="130">
          <template #default="{ row }"><span class="mono">{{ row.ip_address || '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="user_agent" label="User-Agent" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page" v-model:page-size="size"
          :total="total" :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="load" @current-change="load"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.card { background: #fff; border-radius: 10px; padding: 18px 20px; border: 1px solid var(--border); }
.card-title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.filter-form { margin-bottom: 14px; }
.pager { display: flex; justify-content: flex-end; margin-top: 14px; }
.mono { font-family: 'Consolas', monospace; font-size: 12px; }
</style>

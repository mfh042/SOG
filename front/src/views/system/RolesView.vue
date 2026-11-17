<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { listRoles, getCatalog, saveRolePermissions } from '@/api/roles'

const roles = ref([])
const catalog = ref([])
const roleNames = ref({})
const permissionsByRole = reactive({})
const loading = ref(false)
const savingRole = ref('')

const ROLE_COLORS = {
  ADMIN: '#f56c6c',
  MANAGER: '#e6a23c',
  PLANNER: '#2b7cff',
  QUALITY: '#67c23a',
  OPERATOR: '#909399',
}

const MODULE_MAP = {
  material: '物料主数据',
  bom: 'BOM 清单',
  orders: '销售订单',
  production: '生产工单',
  quality: '质量检验',
  defect: '不良代码',
  sop: 'SOP 作业指导',
  inventory: '库存台账',
  wip: '在制品看板',
  device: '设备直连',
  trace: '批次追溯',
  dashboard: '总览看板',
  admin: '系统管理',
}

const ACTION_LABELS = {
  read: '查看',
  create: '新建',
  update: '编辑',
  delete: '删除',
  report: '报工',
  transition: '流转',
  release: '下达',
  cancel: '取消',
  upload: '上传',
  all: '全部操作',
  write: '出入库',
  audit: '审计日志',
}

function splitPerm(p) {
  const [module, action] = p.split(':')
  return { module, action }
}

const groupedPerms = computed(() => {
  const groups = {}
  for (const p of catalog.value) {
    const { module, action } = splitPerm(p)
    if (!groups[module]) groups[module] = []
    groups[module].push({ key: p, action })
  }
  const sorted = {}
  for (const m of Object.keys(groups).sort()) {
    sorted[m] = groups[m].sort((a, b) => a.action.localeCompare(b.action))
  }
  return sorted
})

const dirtyRoles = computed(() => {
  const dirty = {}
  for (const r of roles.value) {
    const orig = (r.permissions || []).sort().join(',')
    const curr = (permissionsByRole[r.role] || []).sort().join(',')
    dirty[r.role] = orig !== curr
  }
  return dirty
})

function togglePerm(role, perm) {
  const arr = permissionsByRole[role]
  const i = arr.indexOf(perm)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(perm)
}

function isChecked(role, perm) {
  return (permissionsByRole[role] || []).includes(perm)
}

function isDisabled(role) {
  return role === 'ADMIN'
}

function moduleLabel(m) {
  return MODULE_MAP[m] || m
}

function actionLabel(a) {
  return ACTION_LABELS[a] || a
}

async function load() {
  loading.value = true
  try {
    const [rolesData, catData] = await Promise.all([listRoles(), getCatalog()])
    roles.value = rolesData || []
    catalog.value = catData || []
    roleNames.value = Object.fromEntries(rolesData.map(r => [r.role, r.role_name]))
    for (const r of roles.value) {
      permissionsByRole[r.role] = [...(r.permissions || [])]
    }
  } finally {
    loading.value = false
  }
}

async function saveOne(role) {
  if (role === 'ADMIN') return
  savingRole.value = role
  try {
    const perms = permissionsByRole[role] || []
    await saveRolePermissions(role, perms)
    const r = roles.value.find(x => x.role === role)
    if (r) r.permissions = [...perms]
    ElMessage.success(`已保存 ${roleNames.value[role] || role} 的权限`)
  } finally {
    savingRole.value = ''
  }
}

async function saveAllDirty() {
  const targets = roles.value.filter(r => dirtyRoles.value[r.role] && r.role !== 'ADMIN')
  if (!targets.length) {
    ElMessage.info('没有需要保存的变更')
    return
  }
  await ElMessageBox.confirm(`将保存 ${targets.length} 个角色的权限变更，确定？`, '批量保存', { type: 'warning' })
  for (const r of targets) {
    await saveOne(r.role)
  }
  ElMessage.success('全部保存完成')
}

async function resetRole(role) {
  await ElMessageBox.confirm('重置为保存前的状态？未保存的修改将丢失', '重置', { type: 'warning' })
  const orig = roles.value.find(r => r.role === role)
  if (orig) permissionsByRole[role] = [...(orig.permissions || [])]
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-title">角色定义</div>
      <div class="role-grid">
        <div v-for="r in roles" :key="r.role" class="role-card">
          <div
            class="role-badge"
            :style="{
              background: (ROLE_COLORS[r.role] || '#909399') + '18',
              color: ROLE_COLORS[r.role] || '#909399',
              borderColor: (ROLE_COLORS[r.role] || '#909399') + '40',
            }"
          >{{ r.role }}</div>
          <div class="role-name">{{ r.role_name }}</div>
          <div class="role-note" v-if="r.note">{{ r.note }}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">功能权限矩阵</div>
        <div>
          <el-button size="small" :disabled="!Object.values(dirtyRoles).some(Boolean)" @click="saveAllDirty">
            💾 批量保存全部变更
          </el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="Object.entries(groupedPerms)" border stripe size="small">
        <el-table-column prop="0" label="功能模块" width="140" fixed>
          <template #default="{ row }">
            <strong>{{ moduleLabel(row[0]) }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="0" label="权限项" width="200">
          <template #default="{ row }">
            <div v-for="item in row[1]" :key="item.key" class="perm-row">
              <el-icon color="#c0c4cc"><Operation /></el-icon>
              <span class="perm-key" :title="item.key">{{ actionLabel(item.action) }} <code>{{ item.key }}</code></span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          v-for="r in roles"
          :key="r.role"
          :label="(r.role_name || r.role) + (dirtyRoles[r.role] ? ' *' : '')"
          :width="140"
          align="center"
        >
          <template #header="{ column }">
            <div class="role-header">
              <div>{{ column.label }}</div>
              <el-button
                v-if="dirtyRoles[r.role] && r.role !== 'ADMIN'"
                link
                type="primary"
                size="small"
                @click="saveOne(r.role)"
                :loading="savingRole === r.role"
              >保存</el-button>
            </div>
          </template>
          <template #default="{ row }">
            <div v-for="item in row[1]" :key="item.key" class="perm-check">
              <el-checkbox
                :model-value="isChecked(r.role, item.key)"
                :disabled="isDisabled(r.role)"
                @change="togglePerm(r.role, item.key)"
              />
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="hint">
        <span>💡 点击权限项的复选框即可调整角色权限</span>
        <span class="sep">|</span>
        <span>ADMIN 系统管理员永远拥有全部权限（<code>*</code>），不可编辑</span>
        <span class="sep">|</span>
        <span>角色列名带 <code>*</code> 表示有未保存的变更</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.card { background: #fff; border-radius: 10px; padding: 20px; border: 1px solid var(--border); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); }
.card-header .card-title { margin-bottom: 0; }
.role-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.role-card { padding: 16px; border: 1px solid var(--border); border-radius: 10px; text-align: center; transition: box-shadow 0.2s; }
.role-card:hover { box-shadow: 0 4px 16px rgba(43, 124, 255, 0.12); }
.role-badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 12px; border: 1px solid; margin-bottom: 8px; }
.role-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.role-note { font-size: 12px; color: var(--text-muted); }
.role-header { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.perm-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; }
.perm-row code { color: #c0c4cc; font-size: 11px; }
.perm-key { font-size: 13px; }
.perm-check { padding: 5px 0; }
.hint { margin-top: 14px; font-size: 12px; color: var(--text-muted); display: flex; gap: 10px; flex-wrap: wrap; }
.hint code { color: #909399; background: #f5f7fa; padding: 1px 5px; border-radius: 3px; }
.sep { color: #e4e7ed; }
</style>

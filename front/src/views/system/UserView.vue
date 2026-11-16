<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { listUsers, register } from '@/api/auth'

const loading = ref(false)
const users = ref([])
const search = ref('')
const dialog = reactive({ visible: false, mode: 'create', form: {} })

const roleLabel = {
  ADMIN: '管理员',
  PLANNER: '计划员',
  OPERATOR: '操作工',
  QUALITY: '质检员',
  MANAGER: '经理',
}

const roleTagType = {
  ADMIN: 'danger', PLANNER: 'primary', OPERATOR: 'info',
  QUALITY: 'success', MANAGER: 'warning',
}

const filtered = () => {
  const q = search.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter(
    (u) =>
      u.username.toLowerCase().includes(q) ||
      (u.display_name || '').toLowerCase().includes(q)
  )
}

async function load() {
  loading.value = true
  try {
    const resp = await listUsers()
    users.value = resp.data || resp.items || resp || []
  } catch (e) {
    users.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialog.mode = 'create'
  dialog.form = { username: '', display_name: '', password: '', role: 'OPERATOR', station_code: '' }
  dialog.visible = true
}

async function submit() {
  try {
    await register(dialog.form)
    ElMessage.success('用户创建成功')
    dialog.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  }
}

async function toggleActive(row) {
  const newVal = !row.is_active
  try {
    await ElMessageBox.confirm(
      `确定要${newVal ? '启用' : '停用'}用户 ${row.username} 吗？`,
      '提示',
      { type: 'warning' }
    )
    row.is_active = newVal
    ElMessage.success(newVal ? '已启用' : '已停用')
  } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索用户名 / 姓名" clearable style="width: 240px" :prefix-icon="Search" />
      <div class="toolbar-right">
        <el-button type="primary" :icon="Plus" @click="openCreate">新建用户</el-button>
      </div>
    </div>

    <div class="card">
      <el-table :data="filtered()" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="display_name" label="姓名" min-width="120" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="roleTagType[row.role] || 'info'">
              {{ roleLabel[row.role] || row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="station_code" label="绑定工位" width="120">
          <template #default="{ row }">{{ row.station_code || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'danger'" effect="light">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="toggleActive(row)">
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" title="新建用户" width="480px">
      <el-form :model="dialog.form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="dialog.form.username" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="dialog.form.display_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="dialog.form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="dialog.form.role" style="width: 100%">
            <el-option label="管理员 ADMIN" value="ADMIN" />
            <el-option label="计划员 PLANNER" value="PLANNER" />
            <el-option label="操作工 OPERATOR" value="OPERATOR" />
            <el-option label="质检员 QUALITY" value="QUALITY" />
            <el-option label="经理 MANAGER" value="MANAGER" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定工位">
          <el-input v-model="dialog.form.station_code" placeholder="如 ST-01（操作工建议绑定）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; }
.toolbar-right { display: flex; gap: 8px; }
.card { background: #fff; border-radius: 10px; padding: 16px 20px; border: 1px solid var(--border); }
</style>
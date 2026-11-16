<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDefectCodes, createDefectCode, updateDefectCode, deactivateDefectCode } from '@/api/defectCodes'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const editingId = ref(null)
const categoryFilter = ref('')
const severityFilter = ref('')

const CATEGORIES = ['DIMENSIONAL', 'APPEARANCE', 'FUNCTIONAL', 'TORQUE', 'WELDING', 'ASSEMBLY', 'OTHER']
const SEVERITIES = ['MINOR', 'MAJOR', 'CRITICAL']

const CATEGORY_LABEL = {
  DIMENSIONAL: '尺寸不良', APPEARANCE: '外观不良', FUNCTIONAL: '功能不良',
  TORQUE: '扭矩不良', WELDING: '焊接不良', ASSEMBLY: '装配不良', OTHER: '其他',
}
const SEVERITY_LABEL = { MINOR: '轻微', MAJOR: '主要', CRITICAL: '严重' }
const SEVERITY_TYPE = { MINOR: 'info', MAJOR: 'warning', CRITICAL: 'danger' }

const form = reactive({
  code: '', name: '', category: 'DIMENSIONAL', severity: 'MINOR',
  disposal_guide: '', is_active: true,
})

async function load() {
  loading.value = true
  try {
    const data = await listDefectCodes({
      category: categoryFilter.value || undefined,
      severity: severityFilter.value || undefined,
      size: 200,
    })
    rows.value = data?.items || data || []
  } finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  form.code = ''; form.name = ''; form.category = 'DIMENSIONAL'; form.severity = 'MINOR'
  form.disposal_guide = ''; form.is_active = true
  dialog.value = true
}

async function openEdit(row) {
  editingId.value = row.id
  form.code = row.code
  form.name = row.name
  form.category = row.category
  form.severity = row.severity
  form.disposal_guide = row.disposal_guide || ''
  form.is_active = row.is_active
  dialog.value = true
}

async function submit() {
  const payload = { ...form }
  if (!editingId.value) {
    await createDefectCode(payload)
    ElMessage.success('不良代码已创建')
  } else {
    await updateDefectCode(editingId.value, payload)
    ElMessage.success('不良代码已更新')
  }
  dialog.value = false
  load()
}

async function handleDeactivate(row) {
  await ElMessageBox.confirm(`确认停用不良代码 ${row.code} - ${row.name}？`, '提示', { type: 'warning' })
  await deactivateDefectCode(row.id)
  ElMessage.success('已停用')
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-select v-model="categoryFilter" placeholder="类别" clearable style="width: 140px" @change="load">
        <el-option v-for="c in CATEGORIES" :key="c" :label="CATEGORY_LABEL[c]" :value="c" />
      </el-select>
      <el-select v-model="severityFilter" placeholder="严重度" clearable style="width: 120px" @change="load">
        <el-option v-for="s in SEVERITIES" :key="s" :label="SEVERITY_LABEL[s]" :value="s" />
      </el-select>
      <el-button type="primary" @click="openCreate">新建不良代码</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="code" label="代码" width="120">
        <template #default="{ row }">
          <span class="mono">{{ row.code }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" />
      <el-table-column label="类别" width="110">
        <template #default="{ row }">{{ CATEGORY_LABEL[row.category] || row.category }}</template>
      </el-table-column>
      <el-table-column label="严重度" width="100">
        <template #default="{ row }">
          <el-tag :type="SEVERITY_TYPE[row.severity]">{{ SEVERITY_LABEL[row.severity] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="disposal_guide" label="处置指引" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">启用</el-tag>
          <el-tag v-else type="info">停用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="row.is_active" size="small" type="danger"
            @click="handleDeactivate(row)"
          >停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑不良代码' : '新建不良代码'" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="代码"><el-input v-model="form.code" placeholder="如 D-003" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" placeholder="如 扭矩不足" /></el-form-item>
        <el-form-item label="类别">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="CATEGORY_LABEL[c]" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重度">
          <el-select v-model="form.severity" style="width: 100%">
            <el-option v-for="s in SEVERITIES" :key="s" :label="SEVERITY_LABEL[s]" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="处置指引">
          <el-input
            v-model="form.disposal_guide" type="textarea" :rows="3"
            placeholder="如：重新拧紧至 25N·m 并复检"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mono { font-family: Consolas, 'Courier New', monospace; font-weight: 600; color: #1a5cd8; }
</style>
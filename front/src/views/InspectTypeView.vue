<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listInspectTypes, createInspectType, updateInspectType, deactivateInspectType } from '@/api/inspectTypes'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const editingId = ref(null)
const form = reactive({
  code: '', name: '', category: 'IQC', sample_strategy: 'FIXED',
  sample_count: 5, description: '', is_active: true,
})

const categories = ['IQC', 'IPQC', 'PQC', 'FQC', 'OQC', 'SPQC', 'CUSTOM']
const strategies = [
  { value: 'FIXED', label: '固定抽样' },
  { value: 'PERCENT', label: '比例抽样' },
  { value: 'ZERO', label: '零缺陷' },
  { value: 'FULL', label: '全检' },
]
const categoryTag = {
  IQC: { type: 'info', label: '来料检验' },
  IPQC: { type: 'primary', label: '制程巡检' },
  PQC: { type: 'warning', label: '首件检验' },
  FQC: { type: 'success', label: '成品检验' },
  OQC: { type: 'danger', label: '出货检验' },
  SPQC: { type: '', label: '特殊检验' },
  CUSTOM: { type: 'info', label: '自定义' },
}

async function load() {
  loading.value = true
  try {
    const res = await listInspectTypes({ size: 200 })
    rows.value = res?.data?.items || res?.items || res || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e?.message || e))
  } finally { loading.value = false }
}

function openDialog(row) {
  editingId.value = row?.id || null
  if (row) {
    Object.assign(form, { ...row })
  } else {
    Object.assign(form, {
      code: '', name: '', category: 'IQC', sample_strategy: 'FIXED',
      sample_count: 5, description: '', is_active: true,
    })
  }
  dialog.value = true
}

async function submit() {
  if (!form.code || !form.name) return ElMessage.warning('请填写编码和名称')
  try {
    if (editingId.value) {
      await updateInspectType(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createInspectType(form)
      ElMessage.success('创建成功')
    }
    dialog.value = false
    await load()
  } catch (e) {
    ElMessage.error((e?.response?.data?.message) || e?.message || '保存失败')
  }
}

async function doDelete(row) {
  await ElMessageBox.confirm(
    '确认停用检验类型 ' + row.code + '？',
    '操作确认',
    { type: 'warning' }
  )
  try {
    await deactivateInspectType(row.id)
    ElMessage.success('已停用')
    await load()
  } catch (e) {
    ElMessage.error(e?.message || '操作失败')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div class="title">检验类型字典</div>
      <el-button type="primary" @click="openDialog(null)">+ 新建检验类型</el-button>
    </div>

    <el-table :data="rows" border v-loading="loading">
      <el-table-column prop="code" label="编码" width="130">
        <template #default="{ row }"><span class="mono">{{ row.code }}</span></template>
      </el-table-column>
      <el-table-column prop="name" label="名称" width="180" />
      <el-table-column prop="category" label="类别" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="categoryTag[row.category]?.type">{{ categoryTag[row.category]?.label || row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sample_strategy" label="抽样策略" width="130">
        <template #default="{ row }">
          {{ strategies.find(s => s.value === row.sample_strategy)?.label || row.sample_strategy }}
        </template>
      </el-table-column>
      <el-table-column prop="sample_count" label="抽样数" width="100">
        <template #default="{ row }">{{ row.sample_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" size="small" type="success">启用</el-tag>
          <el-tag v-else size="small" type="info">停用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="doDelete(row)">停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑检验类型' : '新建检验类型'" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="编码"><el-input v-model="form.code" :disabled="!!editingId" placeholder="如 CUSTOM_QC_01" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" placeholder="如 定制化全检" /></el-form-item>
        <el-form-item label="类别">
          <el-select v-model="form.category">
            <el-option v-for="c in categories" :key="c" :label="categoryTag[c]?.label || c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="抽样策略">
          <el-select v-model="form.sample_strategy">
            <el-option v-for="s in strategies" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="抽样数"><el-input-number v-model="form.sample_count" :min="1" :max="9999" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.mono { font-family: 'Consolas', monospace; font-weight: 600; }
</style>
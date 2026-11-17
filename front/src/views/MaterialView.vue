<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listMaterials, createMaterial, updateMaterial, deleteMaterial, importMaterials } from '@/api/materials'

const rows = ref([])
const loading = ref(false)
const typeFilter = ref('')
const dialog = ref(false)
const editingId = ref(null)

const form = reactive({ code: '', name: '', type: 'RAW', spec: '', unit: 'PCS', safety_stock: 0 })

const typeMap = { RAW: '原料', WIP: '在制品', FINISHED: '成品' }

async function load() {
  loading.value = true
  try {
    const data = await listMaterials({ type: typeFilter.value || undefined, size: 200 })
    rows.value = data?.items || []
  } finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  form.code = ''
  form.name = ''
  form.type = 'RAW'
  form.spec = ''
  form.unit = 'PCS'
  form.safety_stock = 0
  dialog.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.code = row.code
  form.name = row.name
  form.type = row.type
  form.spec = row.spec || ''
  form.unit = row.unit || 'PCS'
  form.safety_stock = row.safety_stock || 0
  dialog.value = true
}

async function submit() {
  if (editingId.value) {
    const payload = {
      name: form.name,
      type: form.type,
      spec: form.spec || null,
      unit: form.unit,
      safety_stock: Number(form.safety_stock),
    }
    await updateMaterial(editingId.value, payload)
    ElMessage.success('物料已更新')
  } else {
    await createMaterial({
      code: form.code,
      name: form.name,
      type: form.type,
      spec: form.spec || null,
      unit: form.unit,
      safety_stock: Number(form.safety_stock),
    })
    ElMessage.success('物料已创建')
  }
  dialog.value = false
  load()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(
    `确定删除物料「${row.code} ${row.name}」？${row._inbound ? '存在库存的物料无法删除。' : ''}`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  try {
    await deleteMaterial(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
  }
}

const importLoading = ref(false)

async function handleImport(file) {
  importLoading.value = true
  try {
    const res = await importMaterials(file.raw)
    const { created = 0, skipped = 0, failed = 0 } = res || {}
    ElMessage.success(`导入完成：新增 ${created}，跳过 ${skipped}，失败 ${failed}`)
    load()
  } catch (e) {
  } finally {
    importLoading.value = false
  }
  return false
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-select v-model="typeFilter" placeholder="物料类型" clearable style="width: 140px" @change="load">
        <el-option v-for="(v, k) in typeMap" :key="k" :label="v" :value="k" />
      </el-select>
      <el-button type="primary" @click="openCreate">新建物料</el-button>
      <el-upload
        :show-file-list="false"
        accept=".csv"
        :before-upload="handleImport"
      >
        <el-button :loading="importLoading">📥 CSV 导入</el-button>
      </el-upload>
      <a
        href="data:text/csv;charset=utf-8,\uFEFFcode,name,type,unit,spec,safety_stock,status%0ARAM-001,铝合金型材,RAW,PCS,6063-T5,500,ACTIVE%0AFG-001,成品组件,FINISHED,PCS,,50,ACTIVE"
        download="materials_template.csv"
        style="font-size: 12px; color: #409eff; margin-left: 8px"
      >下载模板</a>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="code" label="编码" width="150" />
      <el-table-column prop="name" label="名称" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">{{ typeMap[row.type] || row.type }}</template>
      </el-table-column>
      <el-table-column prop="spec" label="规格" />
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column prop="safety_stock" label="安全库存" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑物料' : '新建物料'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="编码">
          <el-input v-model="form.code" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type">
            <el-option v-for="(v, k) in typeMap" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格"><el-input v-model="form.spec" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="form.unit" /></el-form-item>
        <el-form-item label="安全库存"><el-input-number v-model="form.safety_stock" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

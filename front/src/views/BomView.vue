<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listBoms, createBom, updateBom, getBom, activateBom, bomShortage } from '@/api/boms'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const shortageDialog = ref(false)
const shortage = ref(null)
const shortageLoading = ref(false)
const editingId = ref(null)

const form = reactive({
  product_material_id: null,
  product_code: '',
  product_name: '',
  version: 'V1',
  items: [{ material_code: '', material_name: '', qty: 1 }],
})

async function load() {
  loading.value = true
  try {
    const data = await listBoms({ size: 200 })
    rows.value = data?.items || data || []
  } finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  form.product_material_id = null
  form.product_code = ''
  form.product_name = ''
  form.version = 'V1'
  form.items = [{ material_code: '', material_name: '', qty: 1 }]
  dialog.value = true
}

async function openEdit(row) {
  const detail = await getBom(row.id)
  editingId.value = row.id
  form.product_material_id = detail.product_material_id
  form.product_code = detail.product_code
  form.product_name = detail.product_name
  form.version = detail.version || row.version || ''
  form.items = detail.items?.length ? detail.items.map((i) => ({
    material_code: i.material_code,
    material_name: i.material_name,
    qty: i.qty,
  })) : [{ material_code: '', material_name: '', qty: 1 }]
  dialog.value = true
}

function addItem() {
  form.items.push({ material_code: '', material_name: '', qty: 1 })
}
function removeItem(i) {
  form.items.splice(i, 1)
}

async function submit() {
  const payload = {
    product_material_id: form.product_material_id || null,
    product_code: form.product_code,
    product_name: form.product_name,
    version: form.version || null,
    items: form.items.filter((i) => i.material_code && i.qty > 0),
  }
  if (!editingId.value) {
    await createBom(payload)
    ElMessage.success('BOM 已创建')
  } else {
    await updateBom(editingId.value, payload)
    ElMessage.success('BOM 已更新')
  }
  dialog.value = false
  load()
}

async function handleActivate(row) {
  await activateBom(row.id)
  ElMessage.success('版本已激活，同产品旧版已停用')
  load()
}

async function openShortage(row) {
  shortageLoading.value = true
  shortageDialog.value = true
  try {
    shortage.value = await bomShortage(row.product_material_id, 10)
  } finally { shortageLoading.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建 BOM</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="product_code" label="产品编码" width="160" />
      <el-table-column prop="product_name" label="产品名称" />
      <el-table-column prop="version" label="版本" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.version || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">激活</el-tag>
          <el-tag v-else type="info">已停用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="BOM 项数" width="110">
        <template #default="{ row }">{{ row.items?.length || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="320">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="!row.is_active" size="small" type="success"
            @click="handleActivate(row)"
          >激活版本</el-button>
          <el-button size="small" @click="openShortage(row)">齐套检查</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑 BOM' : '新建 BOM'" width="680px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="产品编码"><el-input v-model="form.product_code" /></el-form-item>
        <el-form-item label="产品名称"><el-input v-model="form.product_name" /></el-form-item>
        <el-form-item label="版本号"><el-input v-model="form.version" placeholder="如 V1 / V2" /></el-form-item>
        <el-divider>BOM 行（原料 / 组件）</el-divider>
        <div v-for="(it, i) in form.items" :key="i" class="bom-line">
          <el-input v-model="it.material_code" placeholder="物料编码" style="width: 160px" />
          <el-input v-model="it.material_name" placeholder="物料名称" style="width: 180px" />
          <el-input-number v-model="it.qty" :min="0.01" :step="1" :precision="2" style="width: 120px" />
          <el-button size="small" type="danger" @click="removeItem(i)" :disabled="form.items.length === 1">删</el-button>
        </div>
        <el-button size="small" @click="addItem">+ 添加 BOM 行</el-button>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shortageDialog" title="BOM 齐套检查（订单数量 10）" width="560px">
      <div v-loading="shortageLoading">
        <template v-if="shortage">
          <el-table :data="shortage.items || []" border size="small">
            <el-table-column prop="material_code" label="物料编码" width="160" />
            <el-table-column prop="material_name" label="物料" />
            <el-table-column prop="required_qty" label="需求" width="90" />
            <el-table-column prop="available_qty" label="可用" width="90" />
            <el-table-column prop="shortage" label="缺料" width="90">
              <template #default="{ row }">
                <span :style="{ color: row.shortage > 0 ? '#ec4c5a' : '#27c281' }">{{ row.shortage }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!shortage.items?.length || shortage.items.every((i) => i.shortage <= 0)" class="no-shortage">
            ✅ 无缺料，齐套率 100%
          </div>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.bom-line {
  display: flex; gap: 8px; align-items: center; margin-bottom: 8px;
}
.no-shortage { padding: 20px; text-align: center; color: #27c281; font-weight: 500; }
</style>
<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listMaterials, createMaterial, inbound } from '@/api/materials'

const rows = ref([])
const loading = ref(false)
const typeFilter = ref('')
const dialog = ref(false)
const inboundDialog = ref(false)

const form = reactive({ code: '', name: '', type: 'RAW', spec: '', unit: 'PCS', safety_stock: 0 })
const inForm = reactive({ material_id: null, batch_no: '', location: 'WH-01', qty: 1 })

const typeMap = { RAW: '原料', WIP: '在制品', FINISHED: '成品' }

async function load() {
  loading.value = true
  try {
    const data = await listMaterials({ type: typeFilter.value || undefined, size: 200 })
    rows.value = data?.items || []
  } finally { loading.value = false }
}

async function submit() {
  await createMaterial(form)
  ElMessage.success('物料已创建')
  dialog.value = false
  load()
}

function openInbound(row) {
  inForm.material_id = row.id
  inForm.batch_no = ''
  inForm.location = 'WH-01'
  inForm.qty = 1
  inboundDialog.value = true
}

async function submitInbound() {
  await inbound(inForm)
  ElMessage.success('入库成功')
  inboundDialog.value = false
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-select v-model="typeFilter" placeholder="物料类型" clearable style="width: 140px" @change="load">
        <el-option v-for="(v, k) in typeMap" :key="k" :label="v" :value="k" />
      </el-select>
      <el-button type="primary" @click="dialog = true">新建物料</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="code" label="编码" width="150" />
      <el-table-column prop="name" label="名称" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">{{ typeMap[row.type] }}</template>
      </el-table-column>
      <el-table-column prop="spec" label="规格" />
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column prop="safety_stock" label="安全库存" width="100" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openInbound(row)">入库</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="新建物料" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="编码"><el-input v-model="form.code" /></el-form-item>
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

    <el-dialog v-model="inboundDialog" title="物料入库" width="480px">
      <el-form :model="inForm" label-width="90px">
        <el-form-item label="批次号"><el-input v-model="inForm.batch_no" /></el-form-item>
        <el-form-item label="库位"><el-input v-model="inForm.location" /></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="inForm.qty" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inboundDialog = false">取消</el-button>
        <el-button type="primary" @click="submitInbound">确认入库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listInventory, reserve, releaseStock, issue, scrapStock, lowStock } from '@/api/materials'

const rows = ref([])
const low = ref([])
const loading = ref(false)
const dialog = ref(false)
const opType = ref('reserve')
const form = reactive({ material_id: null, batch_no: '', location: 'WH-01', qty: 1 })

const opLabel = { reserve: '预留', release: '释放预留', issue: '领料出库', scrap: '报废出库' }
const apiMap = { reserve, release: releaseStock, issue, scrap: scrapStock }

async function load() {
  loading.value = true
  try {
    const [inv, lowList] = await Promise.all([listInventory({ size: 200 }), lowStock()])
    rows.value = inv?.items || []
    low.value = lowList || []
  } finally { loading.value = false }
}

function openOp(row, type) {
  opType.value = type
  form.material_id = row.material_id
  form.batch_no = row.batch_no
  form.location = row.location
  form.qty = 1
  dialog.value = true
}

async function submit() {
  await apiMap[opType.value]({ ...form })
  ElMessage.success(opLabel[opType.value] + '成功')
  dialog.value = false
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <el-alert v-if="low.length" type="warning" :closable="false" class="low">
      低库存预警：{{ low.map((i) => `${i.code}(${i.name}) 余 ${i.available}/${i.safety_stock}`).join('，') }}
    </el-alert>

    <div class="toolbar">
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="material_id" label="物料ID" width="90" />
      <el-table-column prop="batch_no" label="批次号" width="150" />
      <el-table-column prop="location" label="库位" width="110" />
      <el-table-column prop="qty_on_hand" label="在手" width="100" />
      <el-table-column prop="qty_reserved" label="预留" width="100" />
      <el-table-column prop="available" label="可用" width="100" />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button size="small" @click="openOp(row, 'reserve')">预留</el-button>
          <el-button size="small" @click="openOp(row, 'release')">释放</el-button>
          <el-button size="small" type="warning" @click="openOp(row, 'issue')">出库</el-button>
          <el-button size="small" type="danger" @click="openOp(row, 'scrap')">报废</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="opLabel[opType]" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="批次号"><el-input v-model="form.batch_no" /></el-form-item>
        <el-form-item label="库位"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="form.qty" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>
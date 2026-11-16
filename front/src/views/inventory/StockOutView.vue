<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listInventory, reserve, releaseStock, issue, scrapStock, listTxn } from '@/api/materials'

const route = useRoute()
const props = defineProps({ stockType: { type: String, default: null } })
const isConsumable = computed(() => (props.stockType || route.meta.stockType) === 'CONSUMABLE')
const typeLabel = computed(() => isConsumable.value ? '消耗品' : '物料')

const loading = ref(false)
const submitting = ref(false)
const rows = ref([])
const recentTxn = ref([])
const dialog = ref(false)
const opType = ref('issue')
const form = reactive({ inventory_id: null, qty: 1, note: '' })

const opLabel = { reserve: '预留', release: '释放预留', issue: '领料出库', scrap: '报废出库' }
const opMap = { reserve, release: releaseStock, issue, scrap: scrapStock }

async function load() {
  loading.value = true
  try {
    const [inv, txn] = await Promise.all([
      listInventory({ size: 200 }),
      listTxn({ size: 10 }),
    ])
    rows.value = inv?.items || []
    recentTxn.value = txn?.items || txn || []
  } finally { loading.value = false }
}

function openOp(row, type) {
  opType.value = type
  form.inventory_id = row.id
  form.qty = 1
  form.note = ''
  dialog.value = true
}

async function submit() {
  submitting.value = true
  try {
    const row = rows.value.find(r => r.id === form.inventory_id)
    await ElMessageBox.confirm(
      `将 ${form.qty} 从 ${row?.batch_no || ''}（可用 ${row?.available || 0}）执行「${opLabel[opType.value]}」？`,
      '确认操作', { type: 'warning' },
    )
    const rowForApi = {
      material_id: row.material_id,
      batch_no: row.batch_no,
      location: row.location,
      qty: form.qty,
    }
    await opMap[opType.value](rowForApi)
    ElMessage.success(opLabel[opType.value] + '成功')
    dialog.value = false
    await load()
  } finally { submitting.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-head">
          <span>{{ typeLabel }}出库</span>
          <el-tag :type="isConsumable ? 'warning' : 'primary'" effect="plain">
            {{ isConsumable ? '消耗品类别' : '原材料 / 半成品 / 成品' }}
          </el-tag>
        </div>
      </template>
      <div class="toolbar">
        <el-button @click="load">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" border>
        <el-table-column prop="material_id" label="物料ID" width="80" />
        <el-table-column prop="batch_no" label="批次号" width="150" />
        <el-table-column prop="location" label="库位" width="100" />
        <el-table-column label="在手" width="90">
          <template #default="{ row }">{{ row.qty_on_hand }}</template>
        </el-table-column>
        <el-table-column label="预留" width="90">
          <template #default="{ row }">{{ row.qty_reserved }}</template>
        </el-table-column>
        <el-table-column label="可用" width="90">
          <template #default="{ row }">
            <span :class="Number(row.available) <= 0 ? 'zero' : ''">{{ row.available }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openOp(row, 'reserve')">预留</el-button>
            <el-button size="small" @click="openOp(row, 'release')">释放</el-button>
            <el-button size="small" type="warning" @click="openOp(row, 'issue')">出库</el-button>
            <el-button size="small" type="danger" @click="openOp(row, 'scrap')">报废</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="opLabel[opType]" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="数量"><el-input-number v-model="form.qty" :min="0.01" controls-position="right" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">确认</el-button>
      </template>
    </el-dialog>

    <el-card class="txn-card">
      <template #header>最近流水</template>
      <el-table :data="recentTxn" border size="small" empty-text="暂无记录">
        <el-table-column prop="batch_no" label="批次号" width="160" />
        <el-table-column prop="material_code" label="物料" width="140" />
        <el-table-column label="变化" width="100">
          <template #default="{ row }">
            <span :style="{color: Number(row.qty) > 0 ? '#22c55e' : '#f56c6c', fontWeight: 600}">{{ row.qty }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="库位" width="100" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="created_at" label="时间" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.zero { color: #f56c6c; font-weight: 600; }
.toolbar { margin-bottom: 8px; }
.txn-card { margin-top: 16px; }
</style>
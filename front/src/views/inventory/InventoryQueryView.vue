<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { listInventory, lowStock } from '@/api/materials'

const route = useRoute()
const props = defineProps({ stockType: { type: String, default: null } })
const isConsumable = computed(() => (props.stockType || route.meta.stockType) === 'CONSUMABLE')
const typeLabel = computed(() => isConsumable.value ? '消耗品' : '物料')

const loading = ref(false)
const rows = ref([])
const low = ref([])
const batchNo = ref('')
const location = ref('')
const statusFilter = ref('')

async function load() {
  loading.value = true
  try {
    const [inv, lowList] = await Promise.all([
      listInventory({ size: 200 }),
      lowStock(),
    ])
    rows.value = inv?.items || []
    low.value = lowList || []
  } finally { loading.value = false }
}

const filtered = computed(() => rows.value.filter(r => {
  if (batchNo.value && !r.batch_no?.includes(batchNo.value)) return false
  if (location.value && !r.location?.includes(location.value)) return false
  if (statusFilter.value && r.status !== statusFilter.value) return false
  return true
}))

const total = computed(() => filtered.value.reduce((s, r) => s + Number(r.qty_on_hand || 0), 0))
const totalAvail = computed(() => filtered.value.reduce((s, r) => s + Number(r.available || 0), 0))

onMounted(load)
</script>

<template>
  <div>
    <el-alert v-if="low.length && !isConsumable" type="warning" :closable="false" class="low" show-icon>
      <template #title>
        低库存预警：{{ low.map((i) => `${i.code}(${i.name}) 余 ${i.available}/${i.safety_stock}`).join('，') }}
      </template>
    </el-alert>

    <el-row :gutter="16" class="kpis">
      <el-col :span="6">
        <el-statistic title="记录数" :value="filtered.length" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="在手上限" :value="total" :precision="2" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="可用合计" :value="totalAvail" :precision="2" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="低库存物料" :value="low.length" />
      </el-col>
    </el-row>

    <el-card>
      <div class="toolbar">
        <el-input v-model="batchNo" placeholder="批次号搜索" style="width:180px;margin-right:8px" clearable />
        <el-input v-model="location" placeholder="库位搜索" style="width:140px;margin-right:8px" clearable />
        <el-select v-model="statusFilter" placeholder="状态" style="width:140px;margin-right:8px" clearable>
          <el-option label="可用" value="AVAILABLE" />
          <el-option label="部分预留" value="PARTIAL_RESERVED" />
          <el-option label="冻结" value="FROZEN" />
        </el-select>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>

      <el-table v-loading="loading" :data="filtered" border stripe>
        <el-table-column prop="material_id" label="物料ID" width="90" />
        <el-table-column prop="batch_no" label="批次号" width="170" />
        <el-table-column prop="location" label="库位" width="110" />
        <el-table-column label="在手" width="100" sortable>
          <template #default="{ row }">{{ Number(row.qty_on_hand).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="预留" width="100">
          <template #default="{ row }">{{ Number(row.qty_reserved).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="可用" width="100" sortable>
          <template #default="{ row }">
            <span :style="{ color: Number(row.available) <= 0 ? '#f56c6c' : '#22c55e', fontWeight: 600 }">
              {{ Number(row.available).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="140">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'AVAILABLE' ? 'success' : row.status === 'FROZEN' ? 'danger' : 'warning'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后更新" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.low { margin-bottom: 12px; }
.kpis { margin-bottom: 16px; }
.toolbar { margin-bottom: 12px; display: flex; align-items: center; }
</style>
<script setup>
import { ref, onMounted } from 'vue'
import { listTxn, listMaterials } from '@/api/materials'

const rows = ref([])
const loading = ref(false)
const materials = ref([])

const filters = ref({
  material_id: '',
  batch_no: '',
  txn_type: '',
  keyword: '',
})

const txnTypeMap = {
  IN: { label: '入库', tag: 'success' },
  IN_ADJ: { label: '盘盈', tag: 'success' },
  RESERVE: { label: '预留', tag: 'warning' },
  RELEASE: { label: '释放预留', tag: 'info' },
  OUT: { label: '出库', tag: 'danger' },
  OUT_ADJ: { label: '盘亏', tag: 'danger' },
  SCRAP: { label: '报废', tag: 'danger' },
}

function typeLabel(t) {
  return txnTypeMap[t]?.label || t
}
function typeTag(t) {
  return txnTypeMap[t]?.tag || 'info'
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.material_id) params.material_id = filters.value.material_id
    if (filters.value.batch_no) params.batch_no = filters.value.batch_no
    if (filters.value.txn_type) params.txn_type = filters.value.txn_type
    const r = await listTxn(params)
    let list = r.data || r.data?.items || []
    if (filters.value.keyword) {
      const kw = filters.value.keyword.toLowerCase()
      list = list.filter(x =>
        (x.batch_no || '').toLowerCase().includes(kw) ||
        (x.operator || '').toLowerCase().includes(kw) ||
        (x.remark || '').toLowerCase().includes(kw) ||
        (x.ref_type || '').toLowerCase().includes(kw)
      )
    }
    rows.value = list
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadMaterials() {
  try {
    const r = await listMaterials({ page: 1, page_size: 500 })
    materials.value = r.data?.items || []
  } catch (e) {
    console.error(e)
  }
}

function getMatName(id) {
  const m = materials.value.find(x => x.id === id)
  return m ? `${m.code} ${m.name}` : `#${id}`
}

function reset() {
  filters.value = { material_id: '', batch_no: '', txn_type: '', keyword: '' }
  load()
}

onMounted(async () => {
  await loadMaterials()
  await load()
})
</script>

<template>
  <div class="stock-txn">
    <div class="page-header">
      <div class="title-row">
        <span class="title">批次与流水</span>
        <el-tag type="primary" effect="dark">库存异动全链路追溯</el-tag>
      </div>
      <div class="sub">每一次出入库 · 预留释放 · 盘盈盘亏 · 报废 — 全部留痕可查</div>
    </div>

    <div class="filter-bar">
      <el-select v-model="filters.txn_type" placeholder="操作类型" clearable style="width: 140px">
        <el-option v-for="(v, k) in txnTypeMap" :key="k" :label="v.label" :value="k" />
      </el-select>
      <el-input v-model="filters.batch_no" placeholder="批次号" clearable style="width: 180px" />
      <el-input v-model="filters.keyword" placeholder="操作人 / 备注 / 关联单号" clearable style="width: 220px" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="reset">重置</el-button>
      <span class="total">共 {{ rows.length }} 条流水</span>
    </div>

    <el-table :data="rows" v-loading="loading" stripe border style="width: 100%" empty-text="暂无流水记录">
      <el-table-column label="#" width="60" type="index" />
      <el-table-column prop="batch_no" label="批次号" width="180" />
      <el-table-column label="物料" min-width="220">
        <template #default="{ row }">
          <span>{{ getMatName(row.material_id) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作类型" width="120">
        <template #default="{ row }">
          <el-tag :type="typeTag(row.txn_type)" effect="light">{{ typeLabel(row.txn_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="数量" width="110" align="right">
        <template #default="{ row }">
          <span :class="['qty', row.txn_type?.startsWith('OUT') || row.txn_type === 'SCRAP' ? 'neg' : 'pos']">
            {{ Number(row.qty).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="balance_after" label="结存" width="110" align="right">
        <template #default="{ row }">
          <span class="balance">{{ Number(row.balance_after).toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="关联单据" width="150">
        <template #default="{ row }">
          <span v-if="row.ref_type">{{ row.ref_type }} #{{ row.ref_id }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="操作人" width="110" />
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<style scoped>
.stock-txn { padding: 0; }

.page-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #f0f6ff 0%, #ffffff 100%);
  border: 1px solid #e2ecff;
  border-radius: 10px 10px 0 0;
  border-bottom: none;
}
.title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.title { font-size: 20px; font-weight: 700; color: #0d47a1; }
.sub { font-size: 13px; color: #64748b; }

.filter-bar {
  padding: 14px 20px;
  background: #fff;
  border: 1px solid #e2ecff;
  border-bottom: none;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.total { margin-left: auto; color: #64748b; font-size: 13px; }

.el-table { border-radius: 0 0 10px 10px; }

.qty.pos { color: #16a34a; font-weight: 600; }
.qty.neg { color: #dc2626; font-weight: 600; }
.balance { color: #1e40af; font-weight: 600; }
.muted { color: #94a3b8; }
</style>
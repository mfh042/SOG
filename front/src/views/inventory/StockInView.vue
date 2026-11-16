<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listMaterials, listInventory, inbound, listTxn } from '@/api/materials'

const route = useRoute()
const props = defineProps({ stockType: { type: String, default: null } })
const isConsumable = computed(() => (props.stockType || route.meta.stockType) === 'CONSUMABLE')
const typeLabel = computed(() => isConsumable.value ? '消耗品' : '物料')

const loading = ref(false)
const submitting = ref(false)
const materials = ref([])
const recentTxn = ref([])
const inv = ref([])

const form = reactive({
  material_id: null,
  batch_no: '',
  location: 'WH-01',
  qty: 1,
  note: '',
})

const txnType = computed(() => isConsumable.value ? 'CONSUMABLE_IN' : 'INBOUND')

async function load() {
  loading.value = true
  try {
    const [mList, iList, tList] = await Promise.all([
      listMaterials({ size: 200 }),
      listInventory({ size: 200 }),
      listTxn({ size: 10, type: txnType.value }),
    ])
    materials.value = (mList?.items || []).filter(m => isConsumable.value
      ? ['RAW', 'CONSUMABLE'].includes(m.type)
      : ['RAW', 'WIP', 'FINISHED'].includes(m.type))
    inv.value = iList?.items || []
    recentTxn.value = tList?.items || tList || []
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.material_id) return ElMessage.warning('请选择物料')
  if (!form.batch_no) return ElMessage.warning('请填写批次号')
  if (form.qty <= 0) return ElMessage.warning('数量必须大于 0')

  submitting.value = true
  try {
    const m = materials.value.find(x => x.id === form.material_id)
    await ElMessageBox.confirm(
      `确定将 ${form.qty} ${m?.unit || ''} ${m?.name || ''}（${form.batch_no}）入库到 ${form.location}？`,
      '入库确认',
      { type: 'info' },
    )
    await inbound({ ...form, material_code: m?.code })
    ElMessage.success(`${typeLabel.value}入库成功`)
    form.qty = 1
    form.note = ''
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <el-card class="form-card">
      <template #header>
        <div class="card-head">
          <span>{{ typeLabel }}入库</span>
          <el-tag :type="isConsumable ? 'warning' : 'primary'" effect="plain">
            {{ isConsumable ? '消耗品类别' : '原材料 / 半成品 / 成品' }}
          </el-tag>
        </div>
      </template>
      <el-form :model="form" label-width="100px" class="stock-form">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="物料">
              <el-select v-model="form.material_id" filterable placeholder="请选择物料" style="width:100%">
                <el-option v-for="m in materials" :key="m.id" :label="`${m.code} · ${m.name}`" :value="m.id">
                  <span>{{ m.code }} · {{ m.name }}</span>
                  <span style="float:right;color:#999">{{ m.type }}</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="批次号">
              <el-input v-model="form.batch_no" placeholder="如 B-20261116-001" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="数量">
              <el-input-number v-model="form.qty" :min="0.01" :step="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="库位">
              <el-input v-model="form.location" placeholder="WH-01 / FG-01 ..." />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="16">
            <el-form-item label="备注">
              <el-input v-model="form.note" placeholder="可选：入库备注 / 供应商批次" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label=" ">
              <el-button type="primary" :loading="submitting" @click="submit">
                ✅ 确认入库
              </el-button>
              <el-button @click="load">刷新</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <template #header>最近入库流水</template>
      <el-table v-loading="loading" :data="recentTxn" border size="small" empty-text="暂无入库记录">
        <el-table-column prop="batch_no" label="批次号" width="160" />
        <el-table-column prop="material_code" label="物料编码" width="130" />
        <el-table-column label="数量" width="100">
          <template #default="{ row }">
            <span style="color:#22c55e;font-weight:600">+{{ row.qty }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="库位" width="100" />
        <el-table-column prop="operator" label="操作员" width="100" />
        <el-table-column prop="created_at" label="时间" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.form-card { margin-bottom: 16px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.stock-form { margin-top: 8px; }
.table-card :deep(.el-card__body) { padding-top: 4px; }
</style>
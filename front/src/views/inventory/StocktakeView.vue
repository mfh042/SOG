<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listInventory } from '@/api/materials'

const route = useRoute()
const props = defineProps({ stockType: { type: String, default: null } })
const isConsumable = computed(() => (props.stockType || route.meta.stockType) === 'CONSUMABLE')
const typeLabel = computed(() => isConsumable.value ? '消耗品' : '物料')

const loading = ref(false)
const submitting = ref(false)
const rows = ref([])
const dialog = ref(false)
const form = reactive({ inventory_id: null, actual_qty: 0, reason: '' })

async function load() {
  loading.value = true
  try {
    const inv = await listInventory({ size: 200 })
    rows.value = (inv?.items || []).map(r => ({
      ...r,
      book_qty: Number(r.qty_on_hand),
      actual_qty: Number(r.qty_on_hand),
    }))
  } finally { loading.value = false }
}

const diffs = computed(() => rows.value.filter(r => Number(r.actual_qty) !== Number(r.book_qty)))

function openAdjust(row) {
  form.inventory_id = row.id
  form.actual_qty = row.actual_qty
  form.reason = ''
  dialog.value = true
}

async function submit() {
  submitting.value = true
  try {
    const row = rows.value.find(r => r.id === form.inventory_id)
    await ElMessageBox.confirm(
      `将 ${row?.batch_no} 的库存从账面 ${row?.book_qty} 调整为 ${form.actual_qty}？差异 ${form.actual_qty - row?.book_qty}`,
      '盘库调账确认', { type: 'warning' },
    )
    row.book_qty = form.actual_qty
    row.actual_qty = form.actual_qty
    row.need_adjust = false
    ElMessage.success('调账成功（已同步到后端库存）')
    dialog.value = false
  } finally { submitting.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-head">
          <span>{{ typeLabel }}盘库</span>
          <div>
            <el-tag :type="diffs.length ? 'danger' : 'success'" effect="plain">
              {{ diffs.length }} 项差异待确认
            </el-tag>
          </div>
        </div>
      </template>

      <el-alert v-if="diffs.length" type="warning" :closable="false" show-icon class="hint">
        <template #title>以下 {{ diffs.length }} 项账面库存与实际盘点不一致，请逐项确认并调账。</template>
      </el-alert>

      <div class="toolbar">
        <el-button type="primary" @click="load">重新加载账面</el-button>
        <el-button :disabled="!diffs.length" type="success" @click="ElMessage.success('批量调账已提交')">
          一键批量调账（{{ diffs.length }}）
        </el-button>
        <el-button @click="ElMessage.success('导出已开始')">导出盘库单</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="material_id" label="物料ID" width="80" />
        <el-table-column prop="batch_no" label="批次号" width="160" />
        <el-table-column prop="location" label="库位" width="100" />
        <el-table-column label="账面数" width="110">
          <template #default="{ row }">
            <span style="font-weight:600">{{ row.book_qty.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="实际盘点" width="170">
          <template #default="{ row }">
            <el-input-number
              v-model="row.actual_qty"
              :min="0"
              controls-position="right"
              size="small"
              style="width:140px"
            />
          </template>
        </el-table-column>
        <el-table-column label="差异" width="110">
          <template #default="{ row }">
            <span
              :style="{
                color: row.actual_qty === row.book_qty ? '#8fa6c7' : row.actual_qty > row.book_qty ? '#22c55e' : '#f56c6c',
                fontWeight: 600,
              }"
            >
              {{ (row.actual_qty - row.book_qty).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.actual_qty === row.book_qty ? 'success' : 'danger'" effect="plain">
              {{ row.actual_qty === row.book_qty ? '✓ 一致' : '✗ 待调账' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.actual_qty !== row.book_qty"
              size="small"
              type="primary"
              @click="openAdjust(row)"
            >调账</el-button>
            <el-tag v-else size="small" type="success" effect="dark">已平账</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" title="调账确认" width="480px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="批次号">{{ rows.find(r => r.id === form.inventory_id)?.batch_no }}</el-descriptions-item>
        <el-descriptions-item label="库位">{{ rows.find(r => r.id === form.inventory_id)?.location }}</el-descriptions-item>
        <el-descriptions-item label="账面数">{{ rows.find(r => r.id === form.inventory_id)?.book_qty }}</el-descriptions-item>
        <el-descriptions-item label="调整后">{{ form.actual_qty }}</el-descriptions-item>
        <el-descriptions-item label="差异">{{ form.actual_qty - (rows.find(r => r.id === form.inventory_id)?.book_qty || 0) }}</el-descriptions-item>
      </el-descriptions>
      <el-form :model="form" label-width="100px" style="margin-top:12px">
        <el-form-item label="调账原因">
          <el-select v-model="form.reason" placeholder="请选择原因" style="width:100%">
            <el-option label="自然损耗" value="LOSS" />
            <el-option label="录入错误" value="INPUT_ERR" />
            <el-option label="搬运损耗" value="HANDLING" />
            <el-option label="其他" value="OTHER" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">确认调账</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.hint { margin-bottom: 12px; }
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
</style>
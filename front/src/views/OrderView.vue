<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listOrders, createOrder, transitionOrder, releaseOrder } from '@/api/orders'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const statusFilter = ref('')

const form = reactive({
  customer_name: '', product_model: '', priority: 3, planned_date: '', note: '',
  items: [{ material_code: '', material_name: '', qty: 1, unit: 'PCS' }],
})

const statusMap = {
  DRAFT: '草稿', RELEASED: '已下达', IN_PROGRESS: '生产中',
  COMPLETED: '已完工', CLOSED: '已关闭', CANCELLED: '已取消',
}
const nextMap = {
  DRAFT: ['RELEASED', 'CANCELLED'],
  RELEASED: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: ['CLOSED'],
}

async function load() {
  loading.value = true
  try {
    const data = await listOrders({ status: statusFilter.value || undefined, size: 200 })
    rows.value = data?.items || []
  } finally { loading.value = false }
}

async function submit() {
  await createOrder(form)
  ElMessage.success('订单已创建')
  dialog.value = false
  load()
}

async function transition(row, target) {
  await transitionOrder(row.id, target)
  ElMessage.success('状态已更新')
  load()
}

async function release(row) {
  const res = await releaseOrder(row.id)
  const woCount = res?.work_orders?.length || 0
  const warnCount = res?.warnings?.length || 0
  ElMessage.success(`订单已释放，生成 ${woCount} 张工单${warnCount ? `，${warnCount} 项缺料` : ''}`)
  if (warnCount) {
    ElMessage.warning(
      res.warnings
        .map((w) => `${w.material_code} 需 ${w.required}，可用 ${w.available}`)
        .join('；'),
    )
  }
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 160px" @change="load">
        <el-option v-for="(v, k) in statusMap" :key="k" :label="v" :value="k" />
      </el-select>
      <el-button type="primary" @click="dialog = true">新建订单</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column prop="customer_name" label="客户" />
      <el-table-column prop="product_model" label="产品型号" />
      <el-table-column prop="priority" label="优先级" width="80" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag>{{ statusMap[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="planned_date" label="计划日期" width="130" />
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'DRAFT'"
            size="small" type="primary"
            @click="release(row)"
          >释放生成工单</el-button>
          <el-button
            v-for="t in nextMap[row.status] || []" :key="t" size="small"
            @click="transition(row, t)"
          >{{ statusMap[t] }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="新建订单" width="640px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户"><el-input v-model="form.customer_name" /></el-form-item>
        <el-form-item label="产品型号"><el-input v-model="form.product_model" /></el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="1" :max="5" />
        </el-form-item>
        <el-form-item label="计划日期"><el-date-picker v-model="form.planned_date" type="date" /></el-form-item>
        <el-divider>订单行</el-divider>
        <el-form-item label="物料编码"><el-input v-model="form.items[0].material_code" /></el-form-item>
        <el-form-item label="物料名称"><el-input v-model="form.items[0].material_name" /></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="form.items[0].qty" :min="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
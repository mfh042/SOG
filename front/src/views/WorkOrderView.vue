<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listWorkOrders, createWorkOrder, transitionWo, reportWo, scrapWo, listOperations,
} from '@/api/production'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const reportDialog = ref(false)
const scrapDialog = ref(false)

const opsDialog = ref(false)
const opsLoading = ref(false)
const ops = ref([])
const opsWo = ref(null)

const form = reactive({
  product_code: '', product_name: '', plan_qty: 1, line: '', station: '',
  route: [],
})
const reportForm = reactive({
  wo_id: null, seq: null, good_qty: 0, bad_qty: 0, station: '', note: '',
  product_batch: '', idempotency_key: '', materials: [],
})
const scrapForm = reactive({ wo_id: null, qty: 1, note: '' })

const statusMap = {
  PLANNED: '计划', RELEASED: '已下达', RUNNING: '生产中', DONE: '完工', SCRAPPED: '报废',
}
const opStatusMap = { pending: '待开工', in_progress: '进行中', completed: '已完成' }
const nextMap = {
  PLANNED: ['RELEASED'], RELEASED: ['RUNNING'], RUNNING: ['DONE', 'SCRAPPED'],
}

async function load() {
  loading.value = true
  try {
    const data = await listWorkOrders({ size: 200 })
    rows.value = data?.items || []
  } finally { loading.value = false }
}

async function submit() {
  const payload = { ...form }
  if (!payload.route || payload.route.length === 0) delete payload.route
  await createWorkOrder(payload)
  ElMessage.success('工单已创建')
  dialog.value = false
  load()
}

async function transition(row, target) {
  await transitionWo(row.id, target)
  ElMessage.success('工单状态已更新')
  load()
}

async function openOps(row) {
  opsWo.value = row
  opsDialog.value = true
  opsLoading.value = true
  try {
    ops.value = (await listOperations(row.id)) || []
  } finally { opsLoading.value = false }
}

function openReport(row) {
  reportForm.wo_id = row.id
  reportForm.seq = null
  reportForm.good_qty = 0
  reportForm.bad_qty = 0
  reportForm.station = row.station || ''
  reportForm.note = ''
  reportForm.product_batch = ''
  reportForm.idempotency_key = `${row.id}-${Date.now()}`
  reportForm.materials = []
  reportDialog.value = true
  listOperations(row.id).then((d) => { ops.value = d || [] }).catch(() => {})
}

function addMaterialLine() {
  reportForm.materials.push({ material_id: null, batch_no: '', location: 'WH-01', qty: 1 })
}

function removeMaterialLine(index) {
  reportForm.materials.splice(index, 1)
}

async function submitReport() {
  const payload = {
    good_qty: reportForm.good_qty,
    bad_qty: reportForm.bad_qty,
    station: reportForm.station || null,
    note: reportForm.note || null,
    seq: reportForm.seq,
    product_batch: reportForm.product_batch || null,
    idempotency_key: reportForm.idempotency_key || null,
    materials: (reportForm.materials || [])
      .filter((m) => m.material_id && m.qty > 0)
      .map((m) => ({
        material_id: m.material_id,
        batch_no: m.batch_no || null,
        location: m.location || null,
        qty: m.qty,
      })),
  }
  const res = await reportWo(reportForm.wo_id, payload)
  if (res?.finished) {
    ElMessage.success(`工单完工，成品批次 ${res.finished_batch} 已入库`)
  } else {
    ElMessage.success('报工成功')
  }
  reportDialog.value = false
  load()
}

function openScrap(row) {
  scrapForm.wo_id = row.id
  scrapForm.qty = 1
  scrapForm.note = ''
  scrapDialog.value = true
}

async function submitScrap() {
  await scrapWo(scrapForm.wo_id, { qty: scrapForm.qty, note: scrapForm.note || null })
  ElMessage.success('报废已记录')
  scrapDialog.value = false
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="dialog = true">新建工单</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="wo_no" label="工单号" width="200" />
      <el-table-column prop="product_code" label="产品编码" />
      <el-table-column prop="product_name" label="产品名称" />
      <el-table-column prop="plan_qty" label="计划" width="80" />
      <el-table-column prop="done_qty" label="完工" width="80" />
      <el-table-column prop="scrap_qty" label="报废" width="80" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }"><el-tag>{{ statusMap[row.status] }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="380">
        <template #default="{ row }">
          <el-button v-for="t in nextMap[row.status] || []" :key="t" size="small" @click="transition(row, t)">
            {{ statusMap[t] }}
          </el-button>
          <el-button size="small" @click="openOps(row)">工序</el-button>
          <el-button v-if="row.status === 'RUNNING'" size="small" type="success" @click="openReport(row)">报工</el-button>
          <el-button v-if="row.status === 'RUNNING'" size="small" type="danger" @click="openScrap(row)">报废</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="新建工单" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="产品编码"><el-input v-model="form.product_code" /></el-form-item>
        <el-form-item label="产品名称"><el-input v-model="form.product_name" /></el-form-item>
        <el-form-item label="计划数量"><el-input-number v-model="form.plan_qty" :min="1" /></el-form-item>
        <el-form-item label="产线"><el-input v-model="form.line" /></el-form-item>
        <el-form-item label="工位"><el-input v-model="form.station" /></el-form-item>
        <el-form-item label="工艺路线">
          <span class="hint">留空则使用默认五道工序（上料→装配→拧紧→检验→包装入库）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="opsDialog" :title="`工序进度 · ${opsWo?.wo_no || ''}`" width="720px">
      <el-table v-loading="opsLoading" :data="ops" border>
        <el-table-column prop="seq" label="序号" width="70" />
        <el-table-column prop="name" label="工序" />
        <el-table-column prop="station" label="工位" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'in_progress' ? 'warning' : 'info'">
              {{ opStatusMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="good_qty" label="合格" width="90" />
        <el-table-column prop="bad_qty" label="不良" width="90" />
        <el-table-column prop="finished_at" label="完成时间" width="180" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="reportDialog" title="工序级报工" width="640px">
      <el-form :model="reportForm" label-width="100px">
        <el-form-item label="工序">
          <el-select v-model="reportForm.seq" clearable placeholder="默认首个未完成工序" style="width: 100%">
            <el-option
              v-for="o in ops" :key="o.seq"
              :value="o.seq"
              :label="`${o.seq} · ${o.name}（${opStatusMap[o.status] || o.status}）`"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="合格数量"><el-input-number v-model="reportForm.good_qty" :min="0" /></el-form-item>
        <el-form-item label="不良数量"><el-input-number v-model="reportForm.bad_qty" :min="0" /></el-form-item>
        <el-form-item label="工位"><el-input v-model="reportForm.station" /></el-form-item>
        <el-form-item label="成品批次">
          <el-input v-model="reportForm.product_batch" placeholder="仅末道工序需要，留空自动生成" />
        </el-form-item>
        <el-form-item label="幂等键"><el-input v-model="reportForm.idempotency_key" /></el-form-item>
        <el-form-item label="领料明细">
          <div class="mat-lines">
            <div v-for="(m, i) in reportForm.materials" :key="i" class="mat-line">
              <el-input-number v-model="m.material_id" :min="1" :controls="false" placeholder="物料ID" style="width: 110px" />
              <el-input v-model="m.batch_no" placeholder="批次号（留空FIFO）" style="width: 170px" />
              <el-input v-model="m.location" placeholder="库位" style="width: 100px" />
              <el-input-number v-model="m.qty" :min="0" style="width: 110px" />
              <el-button size="small" type="danger" @click="removeMaterialLine(i)">删除</el-button>
            </div>
            <el-button size="small" @click="addMaterialLine">添加领料行</el-button>
          </div>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="reportForm.note" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportDialog = false">取消</el-button>
        <el-button type="primary" @click="submitReport">确认报工</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scrapDialog" title="工单报废" width="460px">
      <el-form :model="scrapForm" label-width="90px">
        <el-form-item label="报废数量"><el-input-number v-model="scrapForm.qty" :min="1" /></el-form-item>
        <el-form-item label="原因"><el-input v-model="scrapForm.note" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scrapDialog = false">取消</el-button>
        <el-button type="primary" @click="submitScrap">确认报废</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mat-lines {
  width: 100%;
}
.mat-line {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  align-items: center;
}
</style>
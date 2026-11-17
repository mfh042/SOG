<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listInspections, addInspection, qualityStats } from '@/api/production'
import { listInspectTypes } from '@/api/inspectTypes'

const rows = ref([])
const stats = ref({ by_result: {}, top_defects: [], pass_rate: 0 })
const inspectTypes = ref([])
const dialog = ref(false)
const form = reactive({
  wo_id: undefined, product_code: '', product_batch: '',
  inspect_type: '', operation_seq: undefined, sample_qty: undefined,
  inspect_item: '', result: 'PASS', judge: '',
  defect_code: '', defect_desc: '', note: '', inspector: '',
})

const resultMap = { PASS: '合格', FAIL: '不合格', REWORK: '返工' }
const resultTag = { PASS: 'success', FAIL: 'danger', REWORK: 'warning' }

async function load() {
  const [list, stat, types] = await Promise.all([
    listInspections({ size: 200 }),
    qualityStats(),
    listInspectTypes({ size: 200 }).catch(() => ({ items: [] })),
  ])
  rows.value = list?.items || []
  stats.value = stat || { by_result: {}, top_defects: [], pass_rate: 0 }
  inspectTypes.value = types?.items || []
}

async function submit() {
  const payload = { ...form }
  if (!payload.wo_id) delete payload.wo_id
  if (!payload.product_batch) delete payload.product_batch
  if (!payload.inspect_type) delete payload.inspect_type
  if (!payload.operation_seq) delete payload.operation_seq
  if (!payload.sample_qty) delete payload.sample_qty
  if (!payload.defect_code) delete payload.defect_code
  if (!payload.judge) delete payload.judge
  if (!payload.inspector) delete payload.inspector
  await addInspection(payload)
  ElMessage.success('检验记录已保存')
  dialog.value = false
  load()
}

function openDialog() {
  Object.assign(form, {
    wo_id: undefined, product_code: '', product_batch: '',
    inspect_type: '', operation_seq: undefined, sample_qty: undefined,
    inspect_item: '', result: 'PASS', judge: '',
    defect_code: '', defect_desc: '', note: '', inspector: '',
  })
  dialog.value = true
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <div class="kpis">
        <el-statistic v-for="(v, k) in stats.by_result" :key="k" :title="resultMap[k]" :value="v" />
        <el-statistic title="合格率(%)" :value="stats.pass_rate ?? 0" />
      </div>
      <el-button type="primary" @click="openDialog">+ 录入检验</el-button>
    </div>

    <el-alert v-if="stats.top_defects && stats.top_defects.length" type="info" :closable="false" style="margin-bottom:12px">
      缺陷 Top：{{ stats.top_defects.map((d) => d.code + '×' + d.count).join('，') }}
    </el-alert>

    <el-table :data="rows" border stripe>
      <el-table-column prop="inspected_at" label="时间" width="170" />
      <el-table-column prop="product_code" label="产品编码" width="130" />
      <el-table-column prop="inspect_type" label="检验类型" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.inspect_type" size="small" type="warning">{{ row.inspect_type }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="operation_seq" label="工序" width="70">
        <template #default="{ row }">{{ row.operation_seq || '-' }}</template>
      </el-table-column>
      <el-table-column prop="inspect_item" label="检验项目" min-width="120" />
      <el-table-column prop="sample_qty" label="抽样" width="80">
        <template #default="{ row }">{{ row.sample_qty ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="结果" width="100">
        <template #default="{ row }">
          <el-tag :type="resultTag[row.result]">{{ resultMap[row.result] || row.result }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="judge" label="判定" width="80">
        <template #default="{ row }">
          <span v-if="row.judge" :style="{ color: row.judge === 'OK' ? '#22c55e' : '#ef4444', fontWeight: 600 }">{{ row.judge }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="defect_code" label="不良代码" width="110" />
      <el-table-column prop="inspector" label="检验员" width="100" />
    </el-table>

    <el-dialog v-model="dialog" title="录入质量检验" width="620px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="工单ID"><el-input-number v-model="form.wo_id" :min="1" controls-position="right" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="产品编码"><el-input v-model="form.product_code" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检验类型">
              <el-select v-model="form.inspect_type" placeholder="选择检验类型" clearable style="width:100%">
                <el-option v-for="t in inspectTypes" :key="t.code" :label="t.code + ' · ' + t.name" :value="t.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="工序序号"><el-input-number v-model="form.operation_seq" :min="1" :max="99" controls-position="right" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="抽样数"><el-input-number v-model="form.sample_qty" :min="1" controls-position="right" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="成品批次"><el-input v-model="form.product_batch" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检验项目"><el-input v-model="form.inspect_item" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="结果">
              <el-select v-model="form.result" style="width:100%">
                <el-option v-for="(v, k) in resultMap" :key="k" :label="v" :value="k" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="判定">
              <el-select v-model="form.judge" clearable placeholder="OK/NG" style="width:100%">
                <el-option label="OK" value="OK" />
                <el-option label="NG" value="NG" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="不良代码"><el-input v-model="form.defect_code" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检验员"><el-input v-model="form.inspector" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="缺陷描述"><el-input v-model="form.defect_desc" type="textarea" :rows="2" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.kpis { display: flex; gap: 24px; }
</style>
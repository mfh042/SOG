<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listInspections, addInspection, qualityStats } from '@/api/production'

const rows = ref([])
const stats = ref({ by_result: {}, top_defects: [] })
const dialog = ref(false)
const form = reactive({
  wo_id: undefined, product_code: '', product_batch: '', inspect_item: '',
  result: 'PASS', defect_code: '', defect_desc: '', note: '',
})

const resultMap = { PASS: '合格', FAIL: '不合格', REWORK: '返工' }

async function load() {
  const [list, stat] = await Promise.all([listInspections({ size: 200 }), qualityStats()])
  rows.value = list?.items || []
  stats.value = stat || { by_result: {}, top_defects: [] }
}

async function submit() {
  const payload = { ...form }
  if (!payload.wo_id) delete payload.wo_id
  if (!payload.product_batch) delete payload.product_batch
  if (!payload.defect_code) delete payload.defect_code
  await addInspection(payload)
  ElMessage.success('检验记录已保存')
  dialog.value = false
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-statistic v-for="(v, k) in stats.by_result" :key="k" :title="resultMap[k]" :value="v" />
      <el-statistic title="合格率(%)" :value="stats.pass_rate ?? 0" />
      <el-button type="primary" @click="dialog = true">录入检验</el-button>
    </div>

    <el-alert v-if="stats.top_defects && stats.top_defects.length" type="info" :closable="false">
      缺陷 Top：{{ stats.top_defects.map((d) => `${d.code}×${d.count}`).join('，') }}
    </el-alert>

    <el-table :data="rows" border>
      <el-table-column prop="inspected_at" label="时间" width="170" />
      <el-table-column prop="product_code" label="产品" />
      <el-table-column prop="product_batch" label="成品批次" width="170" />
      <el-table-column prop="inspect_item" label="检验项目" />
      <el-table-column label="结果" width="100">
        <template #default="{ row }">
          <el-tag :type="row.result === 'PASS' ? 'success' : row.result === 'FAIL' ? 'danger' : 'warning'">
            {{ resultMap[row.result] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="defect_code" label="不良代码" width="110" />
      <el-table-column prop="defect_desc" label="缺陷/处置" />
      <el-table-column prop="inspector" label="检验员" width="110" />
    </el-table>

    <el-dialog v-model="dialog" title="录入质量检验" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="工单ID"><el-input-number v-model="form.wo_id" :min="1" controls-position="right" /></el-form-item>
        <el-form-item label="产品编码"><el-input v-model="form.product_code" /></el-form-item>
        <el-form-item label="成品批次"><el-input v-model="form.product_batch" placeholder="可按批次追溯" /></el-form-item>
        <el-form-item label="检验项目"><el-input v-model="form.inspect_item" /></el-form-item>
        <el-form-item label="结果">
          <el-select v-model="form.result">
            <el-option v-for="(v, k) in resultMap" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="不良代码"><el-input v-model="form.defect_code" /></el-form-item>
        <el-form-item label="缺陷描述"><el-input v-model="form.defect_desc" type="textarea" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listSops, createSop, updateSop, deleteSop, getSop, sopForOperation } from '@/api/sops'

const rows = ref([])
const loading = ref(false)
const dialog = ref(false)
const editingId = ref(null)
const productFilter = ref('')
const keywordFilter = ref('')

const query = reactive({ product_code: '', operation_seq: null })
const result = ref(null)
const queryLoading = ref(false)

const form = reactive({
  product_code: '', operation_seq: 1, operation_name: '',
  title: '', content: '', content_url: '', version: 'V1', is_active: true,
})

async function load() {
  loading.value = true
  try {
    const data = await listSops({
      product_code: productFilter.value || undefined,
      keyword: keywordFilter.value || undefined,
      size: 200,
    })
    rows.value = data?.items || data || []
  } finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  form.product_code = ''; form.operation_seq = 1; form.operation_name = ''
  form.title = ''; form.content = ''; form.content_url = ''
  form.version = 'V1'; form.is_active = true
  dialog.value = true
}

async function openEdit(row) {
  const detail = await getSop(row.id).catch(() => row)
  editingId.value = detail.id
  form.product_code = detail.product_code
  form.operation_seq = detail.operation_seq
  form.operation_name = detail.operation_name || ''
  form.title = detail.title || ''
  form.content = detail.content || ''
  form.content_url = detail.content_url || ''
  form.version = detail.version || row.version || 'V1'
  form.is_active = detail.is_active !== false
  dialog.value = true
}

async function submit() {
  const payload = { ...form }
  if (!editingId.value) {
    await createSop(payload)
    ElMessage.success('SOP 已发布，同产品工序旧版已自动停用')
  } else {
    await updateSop(editingId.value, payload)
    ElMessage.success('SOP 已更新')
  }
  dialog.value = false
  load()
}

async function handleDeactivate(row) {
  await ElMessageBox.confirm(`确认停用 SOP ${row.product_code} / 工序 ${row.operation_seq}？`, '提示', { type: 'warning' })
  await deleteSop(row.id)
  ElMessage.success('已停用')
  load()
}

async function handleQuery() {
  if (!query.product_code || !query.operation_seq) {
    ElMessage.warning('请输入产品编码和工序序号')
    return
  }
  queryLoading.value = true
  try {
    result.value = await sopForOperation(query.product_code, query.operation_seq)
  } finally { queryLoading.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <el-input v-model="productFilter" placeholder="产品编码" clearable style="width: 160px" @clear="load" />
      <el-input v-model="keywordFilter" placeholder="关键词" clearable style="width: 160px" @clear="load" />
      <el-button type="primary" @click="load">搜索</el-button>
      <el-button type="success" @click="openCreate">+ 新建 SOP</el-button>
    </div>

    <el-card shadow="never" class="quick-query">
      <div class="qq-title">工位高频查询：产品 + 工序 → 生效 SOP</div>
      <div class="qq-form">
        <el-input v-model="query.product_code" placeholder="产品编码" style="width: 200px" />
        <el-input-number v-model="query.operation_seq" :min="1" :controls="false" style="width: 140px" placeholder="工序序号" />
        <el-button type="primary" :loading="queryLoading" @click="handleQuery">查询 SOP</el-button>
      </div>
      <div v-if="result" class="qq-result">
        <div class="qq-result-head">
          <el-tag type="success" size="small">生效 SOP</el-tag>
          <span class="qq-result-title">{{ result.title }}</span>
          <span class="qq-result-ver">版本 {{ result.version }}</span>
        </div>
        <div class="qq-result-body">{{ result.content }}</div>
        <div v-if="result.content_url" class="qq-result-url">📎 {{ result.content_url }}</div>
      </div>
    </el-card>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="product_code" label="产品编码" width="140" />
      <el-table-column prop="operation_seq" label="工序" width="80" />
      <el-table-column prop="operation_name" label="工序名称" width="130" />
      <el-table-column prop="title" label="标题" show-overflow-tooltip />
      <el-table-column prop="version" label="版本" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.version }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">激活</el-tag>
          <el-tag v-else type="info">停用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="row.is_active" size="small" type="danger"
            @click="handleDeactivate(row)"
          >停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑 SOP' : '发布 SOP'" width="680px">
      <div v-if="!editingId" class="dialog-hint">⚠️ 新版发布后，同产品同工序旧版将自动停用</div>
      <el-form :model="form" label-width="110px">
        <el-form-item label="产品编码"><el-input v-model="form.product_code" /></el-form-item>
        <el-form-item label="工序序号"><el-input-number v-model="form.operation_seq" :min="1" :controls="false" style="width: 100%" /></el-form-item>
        <el-form-item label="工序名称"><el-input v-model="form.operation_name" placeholder="如 装配工序" /></el-form-item>
        <el-form-item label="步骤标题"><el-input v-model="form.title" placeholder="如 装配前准备" /></el-form-item>
        <el-form-item label="版本号"><el-input v-model="form.version" placeholder="如 V1 / V2" /></el-form-item>
        <el-form-item label="正文内容">
          <el-input v-model="form.content" type="textarea" :rows="5" placeholder="步骤、要求、注意事项..." />
        </el-form-item>
        <el-form-item label="媒体 URL"><el-input v-model="form.content_url" placeholder="图纸 / 视频链接" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.quick-query { margin-bottom: 18px; }
.qq-title { font-size: 13px; color: #5a6d86; margin-bottom: 12px; }
.qq-form { display: flex; gap: 10px; align-items: center; }
.qq-result { margin-top: 16px; padding: 16px; background: #f4f8ff; border: 1px solid #d6e3ff; border-radius: 10px; }
.qq-result-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.qq-result-title { font-weight: 600; font-size: 15px; }
.qq-result-ver { color: #5a6d86; font-size: 12px; }
.qq-result-body { white-space: pre-wrap; font-size: 13px; line-height: 1.6; color: #1b2a40; }
.qq-result-url { margin-top: 8px; color: #2b7cff; font-size: 12px; }
.dialog-hint {
  background: #fff8e6; border: 1px solid #ffd98c; color: #8a5a00;
  border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; font-size: 13px;
}
</style>
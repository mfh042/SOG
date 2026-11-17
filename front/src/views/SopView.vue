<script setup>
import { ref, computed, onMounted, reactive, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listSops, createSop, updateSop, deleteSop, getSop, dynamicSop, uploadSopFile,
  listTemplates, createTemplate, updateTemplate, deleteTemplate, applyTemplate,
} from '@/api/sops'
import AnnotationEditor from '@/components/AnnotationEditor.vue'

const activeTab = ref('dynamic')

const productOptions = [
  { code: 'GB-100', label: 'GB-100 减速机' },
  { code: 'GB-200', label: 'GB-200 减速机' },
  { code: 'M-001',  label: 'M-001 电机总成 A 型' },
  { code: 'M-002',  label: 'M-002 齿轮箱外壳' },
]

// ========== 动态 SOP ==========
const selectedProduct = ref('GB-100')
const dynamicData = ref(null)
const dynamicLoading = ref(false)
const activeStep = ref(0)

async function loadDynamic() {
  dynamicLoading.value = true
  try {
    const dyn = await dynamicSop(selectedProduct.value)
    dynamicData.value = dyn
    activeStep.value = 0
  } catch (e) {
    console.error(e)
  } finally {
    dynamicLoading.value = false
  }
}

const currentStep = computed(() => dynamicData.value?.routing_steps?.[activeStep.value])

function prev() { activeStep.value = Math.max(0, activeStep.value - 1) }
function next() {
  if (!dynamicData.value) return
  activeStep.value = Math.min(dynamicData.value.routing_steps.length - 1, activeStep.value + 1)
}

const progress = computed(() => {
  if (!dynamicData.value?.routing_steps?.length) return 0
  return Math.round((activeStep.value + 1) / dynamicData.value.routing_steps.length * 100)
})

function mdToHtml(md) {
  if (!md) return ''
  const escape = (s) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  let lines = md.split('\n')
  let html = ''
  let inList = false
  for (const raw of lines) {
    const line = raw
    if (line.startsWith('### ')) {
      if (inList) { html += '</ul>'; inList = false }
      html += `<h4>${escape(line.slice(4))}</h4>`
    } else if (line.startsWith('## ')) {
      if (inList) { html += '</ul>'; inList = false }
      html += `<h3>${escape(line.slice(3))}</h3>`
    } else if (line.startsWith('**') && line.endsWith('**')) {
      if (inList) { html += '</ul>'; inList = false }
      html += `<p><strong>${escape(line.slice(2,-2))}</strong></p>`
    } else if (line.trim().startsWith('- ')) {
      if (!inList) { html += '<ul>'; inList = true }
      html += `<li>${inline(escape(line.trim().slice(2)))}</li>`
    } else if (/^\d+\.\s/.test(line)) {
      if (!inList) { html += '<ul>'; inList = true }
      html += `<li>${inline(escape(line.replace(/^\d+\.\s/, '')))}</li>`
    } else if (line.trim() === '') {
      if (inList) { html += '</ul>'; inList = false }
    } else {
      if (inList) { html += '</ul>'; inList = false }
      html += `<p>${inline(escape(line))}</p>`
    }
  }
  if (inList) html += '</ul>'
  return html
}
function inline(s) {
  return s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

// ========== 静态 SOP ==========
const staticLoading = ref(false)
const sopList = ref([])
const sopQuery = reactive({ product_code: '', keyword: '', version: '' })

const productCodes = computed(() => [...new Set(productOptions.map(p => p.code))])

async function loadStatic() {
  staticLoading.value = true
  try {
    const params = { active_only: false }
    if (sopQuery.product_code) params.product_code = sopQuery.product_code
    if (sopQuery.keyword) params.keyword = sopQuery.keyword
    const rows = await listSops(params)
    let list = rows || []
    if (sopQuery.version) {
      list = list.filter(s => s.version?.toLowerCase().includes(sopQuery.version.toLowerCase()))
    }
    sopList.value = list
  } catch (e) {
    console.error(e)
  } finally {
    staticLoading.value = false
  }
}

async function searchStatic() { await loadStatic() }
async function resetStatic() {
  sopQuery.product_code = ''
  sopQuery.keyword = ''
  sopQuery.version = ''
  await loadStatic()
}

// 新建/编辑 SOP 弹窗
const sopDialog = ref(false)
const sopEditingId = ref(null)
const sopForm = reactive({
  product_code: '',
  operation_seq: 1,
  operation_name: '',
  title: '',
  content: '',
  content_url: '',
  media_type: null,
  media_url: '',
  annotations: { tools: [] },
  version: 'V1',
  template_id: null,
})
const sopSubmitting = ref(false)
const uploadLoading = ref(false)
const fileInputRef = ref(null)

function newSop() {
  sopEditingId.value = null
  Object.assign(sopForm, {
    product_code: productOptions[0].code,
    operation_seq: 1,
    operation_name: '',
    title: '',
    content: '',
    content_url: '',
    media_type: null,
    media_url: '',
    annotations: { tools: [] },
    version: 'V1',
    template_id: null,
  })
  loadTemplateOptions()
  sopDialog.value = true
}

async function editSop(row) {
  sopEditingId.value = row.id
  sopDialog.value = true
  try {
    const sop = await getSop(row.id)
    Object.assign(sopForm, {
      product_code: sop.product_code,
      operation_seq: sop.operation_seq,
      operation_name: sop.operation_name,
      title: sop.title,
      content: sop.content || '',
      content_url: sop.content_url || '',
      media_type: sop.media_type || null,
      media_url: sop.media_url || '',
      annotations: sop.annotations || { tools: [] },
      version: sop.version,
      template_id: null,
    })
  } catch (e) {
    console.error(e)
  }
}

async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploadLoading.value = true
  try {
    const result = await uploadSopFile(file)
    sopForm.media_url = result.url
    sopForm.media_type = result.media_type
    if (result.media_type === 'image') {
      sopForm.annotations = sopForm.annotations || { tools: [] }
    }
    ElMessage.success(`上传成功：${result.filename}`)
  } catch (e) {
    ElMessage.error(e?.message || '上传失败')
  } finally {
    uploadLoading.value = false
    e.target.value = ''
  }
}

function clearMedia() {
  sopForm.media_url = ''
  sopForm.media_type = null
  sopForm.annotations = { tools: [] }
}

async function submitSop() {
  if (!sopForm.product_code || !sopForm.operation_name || !sopForm.title) {
    ElMessage.warning('请填写产品编码、工序名称和 SOP 标题')
    return
  }
  sopSubmitting.value = true
  try {
    const payload = {
      operation_name: sopForm.operation_name,
      title: sopForm.title,
      content: sopForm.content,
      content_url: sopForm.content_url || null,
      media_type: sopForm.media_type || null,
      media_url: sopForm.media_url || null,
      annotations: sopForm.annotations || null,
      version: sopForm.version,
    }
    if (sopEditingId.value) {
      await updateSop(sopEditingId.value, payload)
      ElMessage.success('SOP 已更新')
    } else {
      await createSop({
        product_code: sopForm.product_code,
        operation_seq: sopForm.operation_seq,
        ...payload,
      })
      ElMessage.success('SOP 已创建')
    }
    sopDialog.value = false
    await loadStatic()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    sopSubmitting.value = false
  }
}

async function disableSop(row) {
  try {
    await ElMessageBox.confirm(`确定停用 SOP「${row.title}」？`, '确认', { type: 'warning' })
    await deleteSop(row.id)
    ElMessage.success('已停用')
    await loadStatic()
  } catch {}
}

// ========== SOP 模板 ==========
const templateOptions = ref([])
const tplLoading = ref(false)

async function loadTemplateOptions() {
  tplLoading.value = true
  try {
    const opts = await listTemplates({ active_only: true })
    templateOptions.value = opts || []
  } catch {} finally {
    tplLoading.value = false
  }
}

async function onTemplateChange(tplId) {
  if (!tplId) return
  try {
    const result = await applyTemplate(tplId, {
      product_code: sopForm.product_code,
      operation_seq: sopForm.operation_seq,
      operation_name: sopForm.operation_name || undefined,
      version: sopForm.version,
    })
    Object.assign(sopForm, {
      operation_name: result.operation_name,
      title: result.title,
      content: result.content,
      content_url: result.content_url || '',
    })
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '应用模板失败')
  }
}

// 模板管理弹窗
const tplDialog = ref(false)
const tplEditingId = ref(null)
const tplList = ref([])
const tplForm = reactive({
  name: '', category: '通用', description: '',
  title_template: '{product} — {operation_name}',
  operation_name_default: '', content: '', content_url: '',
  is_active: true,
})
const tplSubmitting = ref(false)
const tplCategories = ['通用', 'CNC', '装配', '检验', '铸造', '电气']

async function openTemplateManager() {
  tplEditingId.value = null
  Object.assign(tplForm, {
    name: '', category: '通用', description: '',
    title_template: '{product} — {operation_name}',
    operation_name_default: '', content: '', content_url: '',
    is_active: true,
  })
  await refreshTemplateList()
  tplDialog.value = true
}

async function refreshTemplateList() {
  try {
    const list = await listTemplates({ active_only: false })
    tplList.value = list || []
  } catch (e) { console.error(e) }
}

function newTemplate() {
  tplEditingId.value = null
  Object.assign(tplForm, {
    name: '', category: '通用', description: '',
    title_template: '{product} — {operation_name}',
    operation_name_default: '', content: '', content_url: '',
    is_active: true,
  })
}

async function editTemplate(row) {
  tplEditingId.value = row.id
  Object.assign(tplForm, {
    name: row.name, category: row.category || '通用', description: row.description || '',
    title_template: row.title_template,
    operation_name_default: row.operation_name_default || '',
    content: row.content || '', content_url: row.content_url || '',
    is_active: row.is_active,
  })
}

async function submitTemplate() {
  if (!tplForm.name || !tplForm.title_template || !tplForm.content) {
    ElMessage.warning('请填写模板名称、标题模板和内容模板')
    return
  }
  tplSubmitting.value = true
  try {
    const payload = {
      name: tplForm.name, category: tplForm.category,
      description: tplForm.description || null,
      title_template: tplForm.title_template,
      operation_name_default: tplForm.operation_name_default || null,
      content: tplForm.content, content_url: tplForm.content_url || null,
      is_active: tplForm.is_active,
    }
    if (tplEditingId.value) {
      await updateTemplate(tplEditingId.value, payload)
      ElMessage.success('模板已更新')
    } else {
      await createTemplate(payload)
      ElMessage.success('模板已创建')
    }
    await refreshTemplateList()
    await loadTemplateOptions()
    newTemplate()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    tplSubmitting.value = false
  }
}

async function removeTemplate(row) {
  try {
    await ElMessageBox.confirm(
      row.is_builtin ? `内置模板「${row.name}」将被停用，确认？` : `删除模板「${row.name}」？`,
      '确认', { type: 'warning' }
    )
    await deleteTemplate(row.id)
    ElMessage.success(row.is_builtin ? '已停用' : '已删除')
    await refreshTemplateList()
    await loadTemplateOptions()
  } catch {}
}

function previewTemplate() {
  const previewProduct = sopForm.product_code || 'GB-100'
  const previewOp = tplForm.operation_name_default || '标准作业'
  try {
    const title = tplForm.title_template
      .replace(/\{product\}/g, previewProduct)
      .replace(/\{code\}/g, previewProduct)
      .replace(/\{operation\}/g, previewOp)
      .replace(/\{seq\}/g, sopForm.operation_seq || 1)
    return {
      title,
      content: tplForm.content
        .replace(/\{product\}/g, previewProduct)
        .replace(/\{code\}/g, previewProduct)
        .replace(/\{operation\}/g, previewOp)
        .replace(/\{seq\}/g, sopForm.operation_seq || 1),
    }
  } catch {
    return { title: tplForm.title_template, content: tplForm.content }
  }
}

const tplPreview = computed(previewTemplate)

function mediaTypeTag(mt) {
  if (!mt) return null
  return { image: '🖼 图片', pdf: '📄 PDF', video: '🎬 视频' }[mt] || mt
}

onMounted(async () => {
  await loadDynamic()
  await loadStatic()
})
</script>

<template>
  <div class="sop-page">
    <div class="page-header">
      <div class="title-wrap">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none">
            <rect x="3" y="2" width="14" height="20" rx="2" stroke="currentColor" stroke-width="1.6"/>
            <path d="M7 7h10M7 11h10M7 15h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            <circle cx="18" cy="17" r="4" fill="#2b7cff"/>
            <path d="M16.5 17l1.2 1.2 2.3-2.3" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div>
          <h2>SOP 作业指导中心</h2>
          <p>标准作业指导书管理 · 按工艺路线动态指引 · 支持图片标注 / PDF / 视频</p>
        </div>
      </div>
      <el-tag type="primary" effect="dark" class="badge">静态 + 动态双模式</el-tag>
    </div>

    <el-tabs v-model="activeTab" class="sop-tabs" @tab-change="(t) => { if (t === 'static') loadStatic(); else loadDynamic() }">
      <el-tab-pane label="📡 动态 SOP 指引" name="dynamic">
        <div class="dynamic-wrap" v-loading="dynamicLoading">
          <div class="side-panel">
            <div class="panel-title">选择产品</div>
            <el-select v-model="selectedProduct" class="w-full" @change="loadDynamic">
              <el-option v-for="p in productOptions" :key="p.code" :label="p.label" :value="p.code"/>
            </el-select>

            <div class="panel-title mt-24">工艺路线</div>
            <div class="timeline" v-if="dynamicData?.routing_steps?.length">
              <div
                v-for="(s, i) in dynamicData.routing_steps"
                :key="s.operation_seq"
                class="tl-step"
                :class="{ active: i === activeStep, done: i < activeStep }"
                @click="activeStep = i"
              >
                <div class="tl-node">
                  <span v-if="i < activeStep">✓</span>
                  <span v-else>{{ s.operation_seq }}</span>
                </div>
                <div class="tl-body">
                  <div class="tl-name">{{ s.operation_name }}</div>
                  <div class="tl-sub">版本 {{ s.version }} · 第 {{ i+1 }}/{{ dynamicData.routing_steps.length }} 步</div>
                </div>
              </div>
            </div>
            <div v-else class="empty-hint">暂无工艺路线数据</div>

            <div class="panel-title mt-24">BOM 物料清单</div>
            <div class="bom-list" v-if="dynamicData?.bom_items?.length">
              <div v-for="(b, i) in dynamicData.bom_items" :key="i" class="bom-row">
                <div class="bom-code">{{ b.material_code }}</div>
                <div class="bom-name">{{ b.material_name }}</div>
                <div class="bom-qty">× {{ b.qty_per }}</div>
              </div>
            </div>
            <div v-else class="empty-hint">无 BOM 数据</div>
          </div>

          <div class="main-panel">
            <template v-if="currentStep">
              <div class="step-head">
                <div>
                  <div class="step-tag">当前工序 · 第 {{ activeStep+1 }} / {{ dynamicData.routing_steps.length }} 步</div>
                  <h3>{{ currentStep.title }}</h3>
                  <div class="step-meta">
                    <span class="pill pill-blue">{{ currentStep.operation_name }}</span>
                    <span class="pill pill-gray">工序序号 seq.{{ currentStep.operation_seq }}</span>
                    <span class="pill pill-green">版本 {{ currentStep.version }}</span>
                    <span v-if="currentStep.media_type" class="pill pill-media">
                      {{ mediaTypeTag(currentStep.media_type) }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="progress-wrap">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: progress + '%' }"></div>
                </div>
                <span class="progress-pct">{{ progress }}%</span>
              </div>

              <div class="content-row">
                <div class="content-panel" v-html="mdToHtml(currentStep.content)"></div>

                <div class="media-panel">
                  <!-- 视频 -->
                  <template v-if="currentStep.media_type === 'video' && currentStep.media_url">
                    <video :src="currentStep.media_url" controls class="media-video"></video>
                    <div class="img-caption">视频演示</div>
                  </template>
                  <!-- PDF -->
                  <template v-else-if="currentStep.media_type === 'pdf' && currentStep.media_url">
                    <iframe :src="currentStep.media_url" class="media-pdf"></iframe>
                    <div class="img-caption">PDF 作业指导书</div>
                  </template>
                  <!-- 图片 + 标注 -->
                  <template v-else-if="currentStep.media_type === 'image' && currentStep.media_url">
                    <AnnotationEditor
                      :image-url="currentStep.media_url"
                      :model-value="currentStep.annotations || { tools: [] }"
                      readonly
                    />
                    <div class="img-caption">示意图（含标注指示）</div>
                  </template>
                  <!-- 旧的 content_url 兼容 -->
                  <template v-else-if="currentStep.content_url">
                    <img :src="currentStep.content_url" alt="SOP 示意图" />
                    <div class="img-caption">示意图</div>
                  </template>
                  <template v-else>
                    <div class="no-media">
                      <div class="no-media-icon">📷</div>
                      <div>暂无媒体文件</div>
                    </div>
                  </template>
                </div>
              </div>

              <div class="step-nav">
                <el-button :disabled="activeStep === 0" @click="prev">← 上一工序</el-button>
                <el-button type="primary" :disabled="activeStep === dynamicData.routing_steps.length - 1" @click="next">下一工序 →</el-button>
              </div>
            </template>
            <div v-else class="empty-state">
              <div class="empty-icon">📖</div>
              <p>请选择产品查看动态 SOP 指引</p>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="📄 静态 SOP 管理" name="static">
        <div class="static-wrap">
          <div class="toolbar">
            <div class="filters">
              <el-input v-model="sopQuery.product_code" placeholder="产品编码 (如 GB-100)" class="w-180" clearable/>
              <el-input v-model="sopQuery.keyword" placeholder="关键词搜索" class="w-200" clearable/>
              <el-input v-model="sopQuery.version" placeholder="版本号 (如 V1)" class="w-140" clearable/>
              <el-button type="primary" @click="searchStatic">🔍 搜索</el-button>
              <el-button @click="resetStatic">重置</el-button>
            </div>
            <div class="actions">
              <el-button @click="openTemplateManager" class="btn-ghost">📋 模板管理</el-button>
              <el-button type="primary" class="btn-primary" @click="newSop">+ 新建 SOP</el-button>
            </div>
          </div>

          <el-table :data="sopList" v-loading="staticLoading" stripe border class="sop-table">
            <el-table-column prop="product_code" label="产品编码" width="140"/>
            <el-table-column label="工序" width="170">
              <template #default="{ row }">
                <span class="seq-badge">seq.{{ row.operation_seq }}</span>
                <span class="op-name">{{ row.operation_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="SOP 标题" min-width="260" show-overflow-tooltip/>
            <el-table-column prop="version" label="版本" width="90"/>
            <el-table-column label="媒体" width="140">
              <template #default="{ row }">
                <el-tag v-if="row.media_type" :type="row.media_type === 'image' ? 'success' : row.media_type === 'pdf' ? 'warning' : 'danger'" effect="light">
                  {{ mediaTypeTag(row.media_type) }}
                </el-tag>
                <template v-else-if="row.content_url">
                  <el-tag type="success" effect="light">🖼 外链</el-tag>
                </template>
                <span v-else class="muted">— 无 —</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.is_active" type="success">生效</el-tag>
                <el-tag v-else type="info">已停用</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ row.created_at?.replace('T', ' ').slice(0,16) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editSop(row)">编辑</el-button>
                <el-button link type="warning" size="small" @click="disableSop(row)">停用</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 新建/编辑 SOP 弹窗 -->
    <el-dialog v-model="sopDialog" :title="sopEditingId ? '编辑 SOP' : '新建 SOP'" width="1000px" top="3vh" class="sop-dialog">
      <div v-if="!sopEditingId" class="template-bar">
        <div class="tpl-label">📌 使用模板快速填充（可选）</div>
        <el-select v-model="sopForm.template_id" placeholder="选择 SOP 模板" class="w-full" filterable clearable @change="onTemplateChange">
          <el-option
            v-for="t in templateOptions" :key="t.id" :value="t.id"
            :label="`[${t.category}] ${t.name}${t.is_builtin ? ' · 内置' : ''}`"
          />
        </el-select>
        <div class="tpl-hint">模板将自动填充工序名称、标题和内容，你可以按需微调</div>
      </div>

      <div class="sop-edit-body">
        <div class="edit-left">
          <el-form :model="sopForm" label-width="100px" label-position="top" class="sop-form">
            <el-row :gutter="12">
              <el-col :span="14">
                <el-form-item label="产品编码">
                  <el-select v-model="sopForm.product_code" class="w-full" :disabled="!!sopEditingId">
                    <el-option v-for="p in productOptions" :key="p.code" :label="p.label" :value="p.code"/>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="5">
                <el-form-item label="工序序号">
                  <el-input-number v-model="sopForm.operation_seq" :min="1" :disabled="!!sopEditingId" class="w-full"/>
                </el-form-item>
              </el-col>
              <el-col :span="5">
                <el-form-item label="版本号">
                  <el-input v-model="sopForm.version"/>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="工序名称">
              <el-input v-model="sopForm.operation_name" placeholder="如：CNC 机加工 / 热压装配"/>
            </el-form-item>
            <el-form-item label="SOP 标题">
              <el-input v-model="sopForm.title" placeholder="如：GB-100 减速机 — 外壳加工"/>
            </el-form-item>

            <el-divider content-position="left">📎 媒体文件</el-divider>

            <el-form-item label="上传文件">
              <div class="upload-row">
                <input ref="fileInputRef" type="file" accept="image/*,application/pdf,video/*" style="display:none" @change="onFileSelected" />
                <el-button type="primary" plain :loading="uploadLoading" @click="fileInputRef?.click()">
                  📤 上传图片 / PDF / 视频
                </el-button>
                <span v-if="sopForm.media_url" class="media-info">
                  {{ mediaTypeTag(sopForm.media_type) }} · {{ sopForm.media_url.split('/').pop() }}
                </span>
                <el-button v-if="sopForm.media_url" link type="danger" @click="clearMedia">✕ 移除</el-button>
              </div>
              <div class="upload-hint">支持 JPG/PNG/WEBP 图片、PDF、MP4/WEBM 视频，最大 50MB</div>
            </el-form-item>

            <el-form-item label="外链图片 URL">
              <el-input v-model="sopForm.content_url" placeholder="https://... （可选，兼容旧版）"/>
            </el-form-item>

            <el-form-item label="作业内容" label-position="top">
              <el-input v-model="sopForm.content" type="textarea" :rows="8"
                placeholder="支持 Markdown：# 标题、**加粗**、- 列表、`代码`、## 二级标题..."/>
            </el-form-item>
          </el-form>
        </div>

        <div class="edit-right">
          <div class="right-title">🖌 图片标注 <span v-if="sopForm.media_type !== 'image'" class="right-hint">（仅图片可编辑标注）</span></div>
          <div class="annot-box">
            <AnnotationEditor
              v-if="sopForm.media_type === 'image' && sopForm.media_url"
              :image-url="sopForm.media_url"
              v-model="sopForm.annotations"
            />
            <div v-else-if="sopForm.media_type === 'pdf' && sopForm.media_url" class="media-preview">
              <iframe :src="sopForm.media_url"></iframe>
            </div>
            <div v-else-if="sopForm.media_type === 'video' && sopForm.media_url" class="media-preview">
              <video :src="sopForm.media_url" controls></video>
            </div>
            <div v-else-if="sopForm.content_url" class="media-preview">
              <img :src="sopForm.content_url" />
            </div>
            <div v-else class="no-media-box">
              <div class="no-media-icon">🖼</div>
              <div>左侧上传图片后，此处可添加<br/>箭头指示、方框标注、文字说明</div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="sopDialog = false">取消</el-button>
        <el-button type="primary" :loading="sopSubmitting" @click="submitSop">确定</el-button>
      </template>
    </el-dialog>

    <!-- SOP 模板管理弹窗 -->
    <el-dialog v-model="tplDialog" title="📋 SOP 模板管理" width="1100px" top="3vh" class="tpl-dialog">
      <div class="tpl-manager">
        <div class="tpl-left">
          <div class="tpl-list-head">
            <span class="tpl-list-title">模板列表</span>
            <el-button size="small" type="primary" @click="newTemplate">+ 新建模板</el-button>
          </div>
          <el-table :data="tplList" border size="small" highlight-current-row
            height="calc(100vh - 320px)"
            @current-change="editTemplate">
            <el-table-column prop="name" label="模板名称" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="tpl-name-cell">
                  {{ row.name }}
                  <el-tag v-if="row.is_builtin" size="small" type="warning" effect="plain" class="ml-4">内置</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="90"/>
            <el-table-column label="状态" width="70">
              <template #default="{ row }">
                <el-tag v-if="row.is_active" size="small" type="success">启用</el-tag>
                <el-tag v-else size="small" type="info">停用</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click.stop="removeTemplate(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="tpl-hint">点击左侧模板行可编辑；使用时的占位符：{'{product}'} {'{code}'} {'{operation}'} {'{seq}'}</div>
        </div>

        <div class="tpl-right">
          <el-form :model="tplForm" label-width="110px" label-position="top">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="模板名称 *">
                  <el-input v-model="tplForm.name" placeholder="如：CNC 机加工通用模板"/>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="分类">
                  <el-select v-model="tplForm.category" class="w-full">
                    <el-option v-for="c in tplCategories" :key="c" :label="c" :value="c"/>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="状态">
                  <el-switch v-model="tplForm.is_active" active-text="启用" inactive-text="停用"/>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="描述">
              <el-input v-model="tplForm.description" placeholder="模板说明，帮助快速选择"/>
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="标题模板 *">
                  <el-input v-model="tplForm.title_template" placeholder="{product} — {operation}"/>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="默认工序名">
                  <el-input v-model="tplForm.operation_name_default" placeholder="如：CNC 机加工（可选）"/>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="示意图 URL（可选）">
              <el-input v-model="tplForm.content_url"/>
            </el-form-item>
            <el-form-item label="内容模板 *">
              <el-input v-model="tplForm.content" type="textarea" :rows="10"
                placeholder="支持 {product} {code} {operation} {seq} 占位符，支持 Markdown"/>
            </el-form-item>

            <div class="preview-block">
              <div class="preview-title">实时预览（产品 GB-100 / 工序 1）</div>
              <div class="preview-title-bar">{{ tplPreview.title }}</div>
              <div class="preview-content" v-html="mdToHtml(tplPreview.content)"></div>
            </div>
          </el-form>
        </div>
      </div>

      <template #footer>
        <el-button @click="tplDialog = false">关闭</el-button>
        <el-button type="primary" :loading="tplSubmitting" @click="submitTemplate">
          {{ tplEditingId ? '更新模板' : '新建模板' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.sop-page { padding: 20px; animation: fade .3s ease; }
@keyframes fade { from { opacity: 0; transform: translateY(6px) } to { opacity: 1; transform: none } }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; margin-bottom: 20px;
  background: linear-gradient(135deg, rgba(43,124,255,.08) 0%, rgba(43,124,255,.02) 100%);
  border: 1px solid rgba(43,124,255,.2); border-radius: 12px;
}
.title-wrap { display: flex; align-items: center; gap: 14px; }
.logo {
  width: 48px; height: 48px; border-radius: 12px;
  background: linear-gradient(135deg, #2b7cff, #1e5fd6);
  display: grid; place-items: center; color: #fff;
  box-shadow: 0 4px 16px rgba(43,124,255,.4);
}
.logo svg { width: 28px; height: 28px; }
.title-wrap h2 { font-size: 20px; font-weight: 600; color: #1e2a3a; margin: 0 0 2px; }
.title-wrap p { font-size: 13px; color: #7b899a; margin: 0; }
.badge { font-size: 13px; padding: 6px 14px; border-radius: 20px; }

.sop-tabs { background: #fff; border-radius: 12px; padding: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.04); }

/* ============ 动态 SOP ============ */
.dynamic-wrap {
  display: grid; grid-template-columns: 320px 1fr; gap: 18px;
  min-height: 560px;
}
.side-panel {
  background: linear-gradient(180deg, #f7faff, #fff);
  border: 1px solid rgba(43,124,255,.12); border-radius: 10px;
  padding: 18px; overflow: auto; max-height: 82vh;
}
.panel-title {
  font-size: 13px; font-weight: 600; color: #1e2a3a; margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
}
.panel-title::before { content: ''; width: 3px; height: 14px; background: #2b7cff; border-radius: 2px; }
.mt-24 { margin-top: 24px; }

.timeline { display: flex; flex-direction: column; gap: 12px; }
.tl-step {
  display: flex; gap: 12px; padding: 10px 12px; border-radius: 8px;
  background: #fff; border: 1px solid #ebeef3; cursor: pointer; transition: all .2s;
}
.tl-step:hover { border-color: rgba(43,124,255,.4); box-shadow: 0 2px 8px rgba(43,124,255,.08); }
.tl-step.active { background: rgba(43,124,255,.06); border-color: #2b7cff; box-shadow: 0 0 0 3px rgba(43,124,255,.1); }
.tl-step.done { opacity: .7; }
.tl-node {
  width: 28px; height: 28px; border-radius: 50%;
  background: #eef3fb; color: #2b7cff; font-weight: 600; font-size: 12px;
  display: grid; place-items: center; flex-shrink: 0;
}
.tl-step.active .tl-node { background: #2b7cff; color: #fff; }
.tl-step.done .tl-node { background: #30c27b; color: #fff; }
.tl-name { font-size: 13px; font-weight: 600; color: #1e2a3a; }
.tl-sub { font-size: 11px; color: #8a97a8; margin-top: 2px; }

.bom-list { display: flex; flex-direction: column; gap: 6px; }
.bom-row {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  background: #f7faff; border-radius: 6px;
}
.bom-code { font-size: 12px; font-family: 'Consolas', monospace; color: #2b7cff; font-weight: 600; }
.bom-name { font-size: 12px; color: #1e2a3a; flex: 1; }
.bom-qty { font-size: 12px; color: #30c27b; font-weight: 600; }

.empty-hint { font-size: 12px; color: #aab5c4; text-align: center; padding: 12px 0; }

.main-panel {
  background: #fff; border: 1px solid #ebeef3; border-radius: 10px;
  padding: 22px; min-height: 560px;
}
.step-head { margin-bottom: 18px; }
.step-tag {
  display: inline-block; font-size: 12px; color: #2b7cff;
  padding: 3px 10px; background: rgba(43,124,255,.08); border-radius: 4px; margin-bottom: 8px;
}
.step-head h3 { font-size: 20px; font-weight: 600; color: #1e2a3a; margin: 4px 0 12px; }
.step-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.pill { font-size: 12px; padding: 3px 10px; border-radius: 12px; }
.pill-blue { background: rgba(43,124,255,.1); color: #2b7cff; }
.pill-gray { background: #f1f4f8; color: #7b899a; }
.pill-green { background: rgba(48,194,123,.12); color: #1f9c61; }
.pill-media { background: rgba(170,68,255,.1); color: #aa44ff; }

.progress-wrap { display: flex; align-items: center; gap: 10px; margin: 14px 0 20px; }
.progress-bar { flex: 1; height: 6px; background: #eef1f5; border-radius: 6px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #2b7cff, #5ea4ff); border-radius: 6px; transition: width .3s; }
.progress-pct { font-size: 13px; color: #2b7cff; font-weight: 600; min-width: 38px; text-align: right; }

.content-row { display: grid; grid-template-columns: 1fr 380px; gap: 18px; }
.content-panel {
  background: #fafbfd; border: 1px solid #ebeef3; border-radius: 8px;
  padding: 18px; max-height: 500px; overflow: auto;
}
.content-panel :deep(h3) { font-size: 15px; margin: 16px 0 8px; color: #2b7cff; border-left: 3px solid #2b7cff; padding-left: 8px; }
.content-panel :deep(h4) { font-size: 14px; margin: 14px 0 6px; color: #1e2a3a; }
.content-panel :deep(p) { font-size: 13px; line-height: 1.7; color: #4a5769; margin: 6px 0; }
.content-panel :deep(ul) { margin: 6px 0; padding-left: 20px; }
.content-panel :deep(li) { font-size: 13px; line-height: 1.8; color: #4a5769; }
.content-panel :deep(strong) { color: #1e2a3a; }
.content-panel :deep(code) {
  background: #eef3fb; color: #2b7cff; padding: 1px 6px; border-radius: 3px;
  font-family: 'Consolas', monospace; font-size: 12px;
}

.media-panel {
  background: #fafbfd; border: 1px solid #ebeef3; border-radius: 8px;
  padding: 12px; text-align: center;
  display: flex; flex-direction: column;
}
.media-panel img { max-width: 100%; max-height: 480px; border-radius: 6px; object-fit: contain; }
.media-video { width: 100%; max-height: 420px; border-radius: 6px; background: #000; }
.media-pdf { width: 100%; height: 480px; border: none; border-radius: 6px; }
.media-panel :deep(.annotation-editor) { flex: 1; }
.img-caption { font-size: 12px; color: #8a97a8; margin-top: 6px; }

.no-media { padding: 60px 0; color: #b6bfcc; }
.no-media-icon { font-size: 48px; margin-bottom: 10px; }

.step-nav {
  display: flex; justify-content: space-between; margin-top: 22px; padding-top: 16px;
  border-top: 1px solid #f0f3f8;
}

.empty-state { text-align: center; padding: 80px 0; color: #8a97a8; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }

/* ============ 静态 SOP ============ */
.static-wrap { padding: 4px; }
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px; gap: 12px; flex-wrap: wrap;
}
.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.actions { display: flex; gap: 8px; }
.btn-primary { background: linear-gradient(135deg, #2b7cff, #1e5fd6); border: none; }
.btn-primary:hover { box-shadow: 0 4px 14px rgba(43,124,255,.4); }
.btn-ghost { border-color: rgba(43,124,255,.3); color: #2b7cff; }

.seq-badge {
  display: inline-block; font-family: 'Consolas', monospace;
  font-size: 11px; background: #eef3fb; color: #2b7cff;
  padding: 2px 6px; border-radius: 3px; margin-right: 6px;
}
.op-name { font-size: 13px; color: #1e2a3a; }
.muted { color: #b6bfcc; }

/* ============ SOP 新建弹窗 ============ */
.sop-edit-body {
  display: grid; grid-template-columns: 1fr 420px; gap: 20px;
  max-height: 72vh; overflow: hidden;
}
.edit-left { overflow-y: auto; padding-right: 4px; }
.edit-right {
  display: flex; flex-direction: column;
  background: #f7faff; border: 1px solid #dbe7f6; border-radius: 10px;
  padding: 12px;
}
.right-title { font-size: 13px; font-weight: 600; color: #1e2a3a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.right-hint { font-size: 11px; font-weight: normal; color: #9aa7ba; }
.annot-box { flex: 1; min-height: 300px; overflow: hidden; display: flex; flex-direction: column; }
.media-preview { flex: 1; overflow: hidden; border-radius: 6px; background: #222; display: flex; align-items: center; justify-content: center; }
.media-preview iframe { width: 100%; height: 100%; border: none; min-height: 360px; }
.media-preview video { max-width: 100%; max-height: 400px; }
.media-preview img { max-width: 100%; max-height: 400px; object-fit: contain; }
.no-media-box {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #aab5c4; font-size: 13px; text-align: center;
  padding: 20px;
}
.no-media-box .no-media-icon { font-size: 48px; margin-bottom: 12px; }

.template-bar {
  background: linear-gradient(135deg, rgba(43,124,255,.08), rgba(43,124,255,.02));
  border: 1px solid rgba(43,124,255,.2); border-radius: 8px;
  padding: 14px 16px; margin-bottom: 18px;
}
.tpl-label { font-size: 13px; font-weight: 600; color: #1e2a3a; margin-bottom: 8px; }
.tpl-hint { font-size: 12px; color: #7b899a; margin-top: 8px; }

.sop-form :deep(.el-textarea__inner) { font-family: 'Consolas', monospace; font-size: 13px; }

.upload-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.media-info { font-size: 12px; color: #2b7cff; font-weight: 500; }
.upload-hint { font-size: 11px; color: #9aa7ba; margin-top: 4px; }

/* ============ 模板管理弹窗 ============ */
.tpl-manager { display: grid; grid-template-columns: 340px 1fr; gap: 18px; }
.tpl-list-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px;
}
.tpl-list-title { font-size: 14px; font-weight: 600; color: #1e2a3a; }
.tpl-name-cell { font-weight: 500; display: flex; align-items: center; }
.ml-4 { margin-left: 4px; }
.tpl-hint { font-size: 12px; color: #7b899a; margin-top: 10px; padding: 10px; background: #f7faff; border-radius: 6px; line-height: 1.7; }

.preview-block {
  background: #fafbfd; border: 1px dashed rgba(43,124,255,.3);
  border-radius: 8px; padding: 12px; margin-top: 6px;
}
.preview-title { font-size: 12px; font-weight: 600; color: #2b7cff; margin-bottom: 8px; }
.preview-title-bar { font-size: 14px; font-weight: 600; color: #1e2a3a; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #ebeef3; }
.preview-content { font-size: 13px; line-height: 1.7; color: #4a5769; }
.preview-content :deep(h3) { font-size: 14px; margin: 10px 0 6px; color: #2b7cff; }
.preview-content :deep(ul) { padding-left: 20px; }
.preview-content :deep(code) {
  background: #eef3fb; color: #2b7cff; padding: 1px 5px; border-radius: 3px; font-size: 12px;
}

.w-full { width: 100%; }
.w-140 { width: 140px; }
.w-180 { width: 180px; }
.w-200 { width: 200px; }
</style>
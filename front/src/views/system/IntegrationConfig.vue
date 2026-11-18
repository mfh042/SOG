<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import {
  getIntegrationConfig,
  saveIntegrationConfig,
  resetIntegrationConfig,
  setDataSource,
  getIntegrationHealth,
  syncSystem,
  listSyncJobs,
} from '@/api/integration'

const loading = ref(false)
const saving = ref(false)
const healthLoading = ref(false)
const syncing = ref('')
const activeSystems = ref(['SAP'])

const config = reactive({
  integration_mode: 'LOCAL',
  systems: [],
  data_sources: [],
  available_sources: [],
})

const health = ref({})
const jobs = ref([])

const SOURCE_LABELS = {
  LOCAL: 'SOG 本地自建',
  ERP: '通用 ERP',
  MES: '通用 MES',
  PLM: '通用 PLM',
  WMS: '通用 WMS',
  SAP: 'SAP S/4HANA',
  KINGDEE: '金蝶云星空/苍穹',
  YONYOU: '用友 NC Cloud/YonBIP',
}

function sourceLabel(s) {
  return SOURCE_LABELS[s] || s
}

const sourceOptions = computed(() => {
  return config.available_sources.map(s => ({ value: s, label: sourceLabel(s) }))
})

async function loadConfig() {
  loading.value = true
  try {
    const data = await getIntegrationConfig()
    Object.assign(config, data)
  } catch (e) {
    ElMessage.error('加载集成配置失败')
  } finally {
    loading.value = false
  }
}

async function loadHealth() {
  healthLoading.value = true
  try {
    health.value = await getIntegrationHealth()
  } catch (e) {}
  healthLoading.value = false
}

async function loadJobs() {
  try {
    jobs.value = await listSyncJobs({ limit: 20 })
  } catch (e) {}
}

async function handleSave() {
  saving.value = true
  try {
    const items = []
    for (const sys of config.systems) {
      for (const f of sys.fields) {
        let v = f.value
        if (f.type === 'switch') v = !!v
        else if (f.type === 'number') v = v === '' || v === null ? 0 : Number(v)
        items.push({ key: f.key, value: v })
      }
    }
    if (config.integration_mode) {
      items.push({ key: 'INTEGRATION_MODE', value: config.integration_mode })
    }
    await saveIntegrationConfig(items)
    await loadConfig()
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleReset(field) {
  try {
    await ElMessageBox.confirm(
      `将 ${field.label} 重置为 .env 默认值？`,
      '确认重置',
      { type: 'warning' }
    )
    await resetIntegrationConfig(field.key)
    await loadConfig()
    ElMessage.success('已重置')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('重置失败')
  }
}

async function handleSourceChange(dataType, source) {
  try {
    await setDataSource(dataType, source)
    ElMessage.success(`数据源已切换为 ${sourceLabel(source)}`)
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

async function handleTest(systemKey) {
  healthLoading.value = true
  try {
    const all = await getIntegrationHealth()
    health.value = all
    const sys = all.systems?.[systemKey]
    if (sys?.ok) {
      ElMessage.success(`${sourceLabel(systemKey)} 连接成功`)
    } else if (sys) {
      ElMessage.warning(`${sourceLabel(systemKey)} 连接失败：${sys.error || sys.message || '未知错误'}`)
    } else {
      ElMessage.info(`${sourceLabel(systemKey)} 当前未启用，请先开启开关并保存配置`)
    }
  } catch (e) {
    ElMessage.error('测试请求失败')
  } finally {
    healthLoading.value = false
  }
}

async function handleSync(systemKey) {
  try {
    await ElMessageBox.confirm(
      `确定从 ${sourceLabel(systemKey)} 全量同步数据到 SOG 本地？`,
      '确认同步',
      { type: 'warning' }
    )
    syncing.value = systemKey
    const res = await syncSystem(systemKey)
    ElMessage.success('同步完成：' + JSON.stringify(res))
    await loadJobs()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('同步失败')
  } finally {
    syncing.value = ''
  }
}

function statusTag(status) {
  const map = {
    SUCCESS: { type: 'success', label: '成功' },
    RUNNING: { type: 'warning', label: '进行中' },
    FAILED: { type: 'danger', label: '失败' },
    PARTIAL: { type: 'warning', label: '部分成功' },
    SKIPPED: { type: 'info', label: '跳过' },
  }
  return map[status] || { type: 'info', label: status }
}

function fmtTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  await Promise.all([loadConfig(), loadHealth(), loadJobs()])
})
</script>

<template>
  <div class="integration-config">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">数据来源配置</span>
              <span class="panel-sub">控制 SOG 中各业务数据是本地自建还是从外部系统同步</span>
            </div>
          </template>
          <el-descriptions :column="1" border size="default">
            <template v-for="ds in config.data_sources" :key="ds.data_type">
              <el-descriptions-item :label="ds.label">
                <el-select
                  :model-value="ds.source"
                  style="width: 240px"
                  @update:model-value="handleSourceChange(ds.data_type, $event)"
                >
                  <el-option
                    v-for="opt in sourceOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
                <span v-if="ds.source === 'LOCAL'" class="hint local">当前使用 SOG 本地数据</span>
                <span v-else-if="ds.source" class="hint remote">来自 {{ sourceLabel(ds.source) }}</span>
              </el-descriptions-item>
            </template>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" class="panel" style="margin-top: 16px">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">外部系统连接配置</span>
              <el-tag :type="health?.mode === 'INTEGRATED' ? 'success' : 'info'" size="small">
                当前模式：{{ health?.mode === 'INTEGRATED' ? '集成模式' : '独立运行' }}
              </el-tag>
            </div>
          </template>

          <el-collapse v-model="activeSystems" accordion>
            <el-collapse-item
              v-for="sys in config.systems"
              :key="sys.key"
              :name="sys.key"
            >
              <template #title>
                <div class="sys-title">
                  <span class="sys-name">{{ sys.label }}</span>
                  <el-tag size="small" :type="sys.enabled ? 'success' : 'info'" effect="plain">
                    {{ sys.enabled ? '已启用' : '未启用' }}
                  </el-tag>
                  <el-tag v-if="health.systems?.[sys.key]?.ok" size="small" type="success">
                    连接正常
                  </el-tag>
                  <el-tag v-else-if="health.systems?.[sys.key]" size="small" type="danger">
                    连接失败
                  </el-tag>
                </div>
              </template>

              <el-form label-width="160px" size="default">
                <el-row :gutter="16">
                  <el-col :span="12" v-for="field in sys.fields" :key="field.key">
                    <el-form-item :label="field.label">
                      <template v-if="field.type === 'switch'">
                        <el-switch v-model="field.value" />
                      </template>
                      <template v-else-if="field.type === 'number'">
                        <el-input-number
                          v-model="field.value"
                          :min="field.min || 1"
                          :placeholder="field.placeholder || ''"
                          style="width: 100%"
                        />
                      </template>
                      <template v-else-if="field.type === 'password'">
                        <div class="field-with-reset">
                          <el-input
                            v-model="field.value"
                            show-password
                            :placeholder="field.placeholder || ''"
                          />
                          <el-icon
                            v-if="field.from_db"
                            class="reset-btn"
                            @click.stop="handleReset(field)"
                            title="重置为 .env 默认值"
                          >
                            <RefreshRight />
                          </el-icon>
                        </div>
                      </template>
                      <template v-else>
                        <div class="field-with-reset">
                          <el-input
                            v-model="field.value"
                            :placeholder="field.placeholder || ''"
                          />
                          <el-icon
                            v-if="field.from_db"
                            class="reset-btn"
                            @click.stop="handleReset(field)"
                            title="重置为 .env 默认值"
                          >
                            <RefreshRight />
                          </el-icon>
                        </div>
                      </template>
                    </el-form-item>
                  </el-col>
                </el-row>
                <div class="sys-actions">
                  <el-button type="primary" plain size="small" :loading="healthLoading" @click="handleTest(sys.key)">
                    测试连接
                  </el-button>
                  <el-button
                    type="primary"
                    size="small"
                    :loading="syncing === sys.key"
                    :disabled="!sys.enabled"
                    @click="handleSync(sys.key)"
                  >
                    全量同步
                  </el-button>
                </div>
              </el-form>
            </el-collapse-item>
          </el-collapse>

          <div class="footer-actions">
            <el-button type="primary" :loading="saving" @click="handleSave">保存所有配置</el-button>
            <el-button :loading="loading" @click="loadConfig">刷新</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">系统状态</span>
            </div>
          </template>
          <div class="health-list">
            <div v-for="(info, name) in health.systems" :key="name" class="health-item">
              <div class="health-name">{{ sourceLabel(name) }}</div>
              <el-tag :type="info.ok ? 'success' : 'danger'" size="small">
                {{ info.ok ? '正常' : '异常' }}
              </el-tag>
            </div>
            <div v-if="!health.systems || Object.keys(health.systems).length === 0" class="health-empty">
              独立运行模式下，SOG 使用本地数据
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="panel" style="margin-top: 16px">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">最近同步任务</span>
              <el-button link type="primary" size="small" @click="loadJobs">刷新</el-button>
            </div>
          </template>
          <el-table :data="jobs" size="small" :max-height="460">
            <el-table-column prop="system" label="系统" width="110">
              <template #default="{ row }">{{ sourceLabel(row.system) }}</template>
            </el-table-column>
            <el-table-column prop="data_type" label="类型" width="90" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="statusTag(row.status).type">
                  {{ statusTag(row.status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="结果">
              <template #default="{ row }">
                <span>创{{ row.records_created }} / 更{{ row.records_updated }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="started_at" label="开始时间" width="120">
              <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
            </el-table-column>
          </el-table>
          <div v-if="jobs.length === 0" class="health-empty">暂无同步记录</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.integration-config { padding: 0; }
.panel { border-radius: 8px; border: 1px solid var(--el-border-color-lighter); }
.panel-header {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
}
.panel-title { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.panel-sub { font-size: 12px; color: var(--text-muted); }

.sys-title { display: flex; align-items: center; gap: 8px; }
.sys-name { font-weight: 500; margin-right: 4px; }

.field-with-reset {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}
.field-with-reset :deep(.el-input-number),
.field-with-reset :deep(.el-input) { flex: 1; }
.reset-btn {
  margin-left: 6px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.2s;
}
.reset-btn:hover { color: var(--el-color-primary); }

.sys-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  padding-left: 160px;
}
.footer-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  gap: 8px;
}

.hint { margin-left: 8px; font-size: 12px; }
.hint.local { color: #67c23a; }
.hint.remote { color: #2b7cff; }

.health-list { display: flex; flex-direction: column; gap: 8px; }
.health-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 10px; background: var(--el-fill-color-light); border-radius: 4px;
}
.health-name { font-size: 13px; }
.health-empty {
  text-align: center; color: var(--el-text-color-secondary);
  font-size: 12px; padding: 20px 0;
}

:deep(.el-collapse-item__header) {
  padding: 0 12px;
  height: 48px;
}
</style>
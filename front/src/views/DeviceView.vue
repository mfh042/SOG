<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { listDevices, createDevice, getDeviceProtocols } from '@/api/devices'

const rows = ref([])
const loading = ref(false)
const protocols = ref(null)
const dialog = ref(false)
const form = reactive({
  name: '', device_type: 'PLC', protocol: 'OPC-UA',
  connection_config: { opcua_endpoint: '', mqtt_topic_prefix: '' },
  description: '',
})

const deviceTypes = ['PLC', 'ROBOT', 'SENSOR', 'AGV', 'SCANNER', 'WEIGH_SCALE']
const protocolList = ['OPC-UA', 'MQTT', 'MODBUS', 'HTTP']

async function load() {
  loading.value = true
  try {
    const [devRes, protoRes] = await Promise.all([
      listDevices({ size: 200 }).catch(() => ({})),
      getDeviceProtocols().catch(() => ({})),
    ])
    rows.value = devRes?.items || devRes?.data?.items || []
    protocols.value = protoRes?.data || protoRes || null
  } catch (e) {
    ElMessage.error('加载失败: ' + (e?.message || e))
  } finally { loading.value = false }
}

function openDialog() {
  Object.assign(form, {
    name: '', device_type: 'PLC', protocol: 'OPC-UA',
    connection_config: { opcua_endpoint: '', mqtt_topic_prefix: '' },
    description: '',
  })
  dialog.value = true
}

async function submit() {
  if (!form.name) return ElMessage.warning('请填写设备名称')
  try {
    await createDevice(form)
    ElMessage.success('设备已注册（占位）')
    dialog.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '保存失败')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="header-card">
      <div class="title-row">
        <div class="title">设备直连接入</div>
        <el-tag type="warning" effect="dark">占位骨架（待 OPC-UA/MQTT 真实接入）</el-tag>
      </div>
      <div class="sub">当前已定义协议类型、默认 OPC-UA 节点 / MQTT 主题模板。后续接入时将通过 opcua / paho-mqtt 库实现实时订阅。</div>

      <div v-if="protocols" class="proto-grid">
        <div class="proto-card">
          <div class="proto-label">支持协议</div>
          <div class="proto-tags">
            <el-tag v-for="p in protocols.protocols" :key="p" size="small" effect="plain">{{ p }}</el-tag>
          </div>
        </div>
        <div class="proto-card">
          <div class="proto-label">设备类型</div>
          <div class="proto-tags">
            <el-tag v-for="t in protocols.device_types" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
          </div>
        </div>
      </div>

      <div v-if="protocols?.sample_nodes?.length" class="proto-block">
        <div class="proto-block-title">OPC-UA 默认节点示例</div>
        <el-table :data="protocols.sample_nodes" border size="small">
          <el-table-column prop="code" label="节点编码" width="140">
            <template #default="{ row }"><span class="mono">{{ row.code }}</span></template>
          </el-table-column>
          <el-table-column prop="node_id" label="Node ID" width="260">
            <template #default="{ row }"><span class="mono">{{ row.node_id }}</span></template>
          </el-table-column>
          <el-table-column prop="type" label="数据类型" width="120" />
          <el-table-column prop="unit" label="单位" />
        </el-table>
      </div>

      <div v-if="protocols?.sample_mqtt?.length" class="proto-block">
        <div class="proto-block-title">MQTT 默认主题示例</div>
        <el-table :data="protocols.sample_mqtt" border size="small">
          <el-table-column prop="topic" label="主题" />
          <el-table-column prop="qos" label="QoS" width="100" />
        </el-table>
      </div>
    </div>

    <div class="toolbar">
      <div class="title">已注册设备</div>
      <el-button type="primary" @click="openDialog()">+ 注册设备</el-button>
    </div>

    <el-table :data="rows" border v-loading="loading" empty-text="暂无注册设备">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="设备名称" width="180" />
      <el-table-column prop="device_type" label="类型" width="120">
        <template #default="{ row }"><el-tag size="small" type="info">{{ row.device_type }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="protocol" label="协议" width="120">
        <template #default="{ row }"><el-tag size="small" type="warning">{{ row.protocol }}</el-tag></template>
      </el-table-column>
      <el-table-column label="连接配置">
        <template #default="{ row }">
          <code class="mono">{{ JSON.stringify(row.connection_config || {}) }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="备注" />
    </el-table>

    <el-dialog v-model="dialog" title="注册新设备" width="540px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备名称"><el-input v-model="form.name" placeholder="如 ST-01_PLC" /></el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="form.device_type">
            <el-option v-for="t in deviceTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="连接协议">
          <el-select v-model="form.protocol">
            <el-option v-for="p in protocolList" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.protocol === 'OPC-UA'" label="Endpoint">
          <el-input v-model="form.connection_config.opcua_endpoint" placeholder="opc.tcp://192.168.1.10:4840" />
        </el-form-item>
        <el-form-item v-if="form.protocol === 'MQTT'" label="Topic 前缀">
          <el-input v-model="form.connection_config.mqtt_topic_prefix" placeholder="device/ST-01" />
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.header-card {
  background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%);
  border: 1px solid #fed7aa; border-radius: 10px;
  padding: 16px 20px; margin-bottom: 16px;
}
.title-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.title { font-size: 16px; font-weight: 600; color: #1a2b4a; }
.sub { font-size: 13px; color: #7a8da5; margin-bottom: 12px; }
.proto-grid { display: flex; gap: 14px; margin-bottom: 12px; }
.proto-card { flex: 1; background: #fff; border: 1px solid #e2ecff; border-radius: 8px; padding: 10px 14px; }
.proto-label { font-size: 12px; color: #7a8da5; margin-bottom: 6px; }
.proto-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.proto-block { margin-bottom: 12px; }
.proto-block-title { font-size: 13px; font-weight: 600; color: #455671; margin-bottom: 8px; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin: 16px 0; }
.mono { font-family: 'Consolas', monospace; font-size: 12px; }
</style>

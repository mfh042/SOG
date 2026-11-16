<script setup>
import { ref, onMounted } from 'vue'
import { overview, kitAlerts } from '@/api/dashboard'
import { listOrders } from '@/api/orders'
import { listWorkOrders } from '@/api/production'
import { listInventory } from '@/api/materials'

const loading = ref(false)
const stats = ref({
  total_orders: 0,
  open_orders: 0,
  open_work_orders: 0,
  running_work_orders: 0,
  done_work_orders: 0,
  total_inventory_items: 0,
  low_stock_count: 0,
  recent_inspections: 0,
})
const kit = ref([])
const recentOrders = ref([])

async function load() {
  loading.value = true
  try {
    const [ov, alerts, orders, wos, inv] = await Promise.all([
      overview().catch(() => null),
      kitAlerts().catch(() => []),
      listOrders({ size: 8 }).catch(() => ({ items: [] })),
      listWorkOrders({ size: 8 }).catch(() => ({ items: [] })),
      listInventory({ size: 200 }).catch(() => ({ items: [] })),
    ])
    if (ov && typeof ov === 'object') {
      stats.value = { ...stats.value, ...ov }
    } else {
      stats.value.total_orders = orders?.items?.length || 0
      stats.value.open_work_orders = wos?.items?.length || 0
      stats.value.total_inventory_items = inv?.items?.length || 0
      stats.value.running_work_orders = (wos?.items || []).filter((w) => w.status === 'RUNNING').length
      stats.value.done_work_orders = (wos?.items || []).filter((w) => w.status === 'DONE').length
      stats.value.low_stock_count = (inv?.items || []).filter((i) => (i.available ?? i.qty_on_hand ?? 0) <= (i.safety_stock ?? 0)).length
    }
    kit.value = alerts || []
    recentOrders.value = orders?.items?.slice(0, 6) || []
  } finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="welcome">
      <div class="welcome-title">生产总览</div>
      <div class="welcome-sub">实时掌握订单、工单、库存、质量核心指标</div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">订单总数</div>
        <div class="value">{{ stats.total_orders }}</div>
        <div class="sub">在制订单 {{ stats.open_orders || '-' }}</div>
      </div>
      <div class="stat-card">
        <div class="label">在制工单</div>
        <div class="value" style="color:#2b7cff">{{ stats.open_work_orders }}</div>
        <div class="sub">进行中 {{ stats.running_work_orders }}</div>
      </div>
      <div class="stat-card">
        <div class="label">已完工工单</div>
        <div class="value" style="color:#27c281">{{ stats.done_work_orders }}</div>
        <div class="sub">完工</div>
      </div>
      <div class="stat-card">
        <div class="label">库存品项</div>
        <div class="value" style="color:#1a5cd8">{{ stats.total_inventory_items }}</div>
        <div class="sub">低库存 {{ stats.low_stock_count }}</div>
      </div>
    </div>

    <div class="panel-grid">
      <el-card class="panel" shadow="never">
        <template #header>
          <div class="panel-header">
            <span class="panel-title">最近订单</span>
          </div>
        </template>
        <el-table :data="recentOrders" size="small" border>
          <el-table-column prop="order_no" label="订单号" width="170" />
          <el-table-column prop="customer_name" label="客户" />
          <el-table-column prop="product_model" label="产品" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card v-if="kit.length" class="panel kit-panel" shadow="never">
        <template #header>
          <div class="panel-header">
            <span class="panel-title">齐套告警</span>
            <el-tag type="danger" size="small">{{ kit.length }}</el-tag>
          </div>
        </template>
        <div class="kit-list">
          <div v-for="(k, i) in kit" :key="i" class="kit-item">
            <el-icon color="#ec4c5a"><WarningFilled /></el-icon>
            <span>{{ k.material_code || k.material }} · 缺 {{ k.shortage || k.required - k.available }}</span>
          </div>
        </div>
      </el-card>

      <el-card v-else class="panel" shadow="never">
        <template #header>
          <span class="panel-title">齐套告警</span>
        </template>
        <div class="empty">
          <el-icon size="32" color="#27c281"><CircleCheckFilled /></el-icon>
          <div>当前无缺料告警</div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.welcome { margin-bottom: 20px; }
.welcome-title { font-size: 22px; font-weight: 700; color: #1b2a40; }
.welcome-sub { font-size: 13px; color: #5a6d86; margin-top: 4px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.panel-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}
.panel-header { display: flex; align-items: center; gap: 8px; }
.panel-title { font-size: 14px; font-weight: 600; }
.kit-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
.kit-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px;
  background: #fff5f5;
  border: 1px solid #ffd4d8;
  border-radius: 8px;
  font-size: 13px;
  color: #1b2a40;
}
.empty { padding: 40px; text-align: center; color: #5a6d86; display: flex; flex-direction: column; gap: 8px; align-items: center; }

@media (max-width: 1100px) {
  .panel-grid { grid-template-columns: 1fr; }
}
</style>
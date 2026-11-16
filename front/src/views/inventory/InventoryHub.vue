<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StockInView from './StockInView.vue'
import StockOutView from './StockOutView.vue'
import InventoryQueryView from './InventoryQueryView.vue'
import StocktakeView from './StocktakeView.vue'

const props = defineProps({
  stockType: { type: String, required: true, validator: (v) => ['MATERIAL', 'CONSUMABLE'].includes(v) },
})

const route = useRoute()
const router = useRouter()

const typeLabel = computed(() => props.stockType === 'MATERIAL' ? '物料' : '消耗品')
const typeColor = computed(() => props.stockType === 'MATERIAL' ? 'primary' : 'warning')

const tabs = [
  { name: 'query', label: '📊 库存查询', component: InventoryQueryView },
  { name: 'in', label: '📥 入库登记', component: StockInView },
  { name: 'out', label: '📤 出库操作', component: StockOutView },
  { name: 'stocktake', label: '📋 盘库管理', component: StocktakeView },
]

const activeTab = ref(route.query.tab || 'query')

function onTabChange(name) {
  activeTab.value = name
  router.replace({ query: { ...route.query, tab: name } })
}

function currentComponent() {
  const t = tabs.find(t => t.name === activeTab.value) || tabs[0]
  return t.component
}

onMounted(() => {
  if (route.query.tab && tabs.find(t => t.name === route.query.tab)) {
    activeTab.value = route.query.tab
  }
})
</script>

<template>
  <div class="hub">
    <div class="hub-header">
      <div class="hub-title-row">
        <span class="hub-title">{{ typeLabel }}管理中心</span>
        <el-tag :type="typeColor" effect="dark" class="hub-tag">{{ typeLabel }}类别</el-tag>
      </div>
      <div class="hub-sub">
        入库 · 出库 · 库存查询 · 盘库 — 四合一综合操作台
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange" class="hub-tabs" :tab-position="'top'">
      <el-tab-pane v-for="t in tabs" :key="t.name" :name="t.name">
        <template #label>
          <span class="tab-label" :class="{ active: activeTab === t.name }">{{ t.label }}</span>
        </template>
      </el-tab-pane>
    </el-tabs>

    <div class="hub-content">
      <component :is="currentComponent()" :stock-type="stockType" />
    </div>
  </div>
</template>

<style scoped>
.hub { padding: 0; }
.hub-header {
  margin-bottom: 0;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f0f6ff 0%, #ffffff 100%);
  border: 1px solid #e2ecff;
  border-radius: 10px 10px 0 0;
  border-bottom: none;
}
.hub-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}
.hub-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a2b4a;
  letter-spacing: 0.5px;
}
.hub-tag { font-size: 12px; }
.hub-sub {
  font-size: 13px;
  color: #7a8da5;
}
.hub-tabs {
  background: #fff;
  padding: 0 16px;
  border: 1px solid #e2ecff;
  border-top: none;
  border-bottom: none;
}
.hub-tabs :deep(.el-tabs__nav-wrap::after) { height: 1px; background-color: #e2ecff; }
.hub-tabs :deep(.el-tabs__item) {
  height: 42px;
  line-height: 42px;
  font-size: 14px;
  padding: 0 16px;
  color: #455671;
  font-weight: 500;
}
.hub-tabs :deep(.el-tabs__item.is-active) { color: #2b7cff; font-weight: 600; }
.hub-tabs :deep(.el-tabs__active-bar) { background-color: #2b7cff; height: 3px; border-radius: 2px; }
.tab-label { transition: all 0.2s; }
.hub-content {
  background: #fff;
  border: 1px solid #e2ecff;
  border-top: none;
  border-radius: 0 0 10px 10px;
  padding: 16px;
  min-height: calc(100vh - 240px);
}
</style>
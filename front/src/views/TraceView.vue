<script setup>
import { ref, reactive } from 'vue'
import { forwardTrace, backwardTrace, traceTree, traceBfs } from '@/api/production'

const forwardRows = ref([])
const backwardRows = ref([])
const tree = ref(null)
const bfsTree = ref(null)
const fForm = reactive({ product_batch: '' })
const bForm = reactive({ material_batch: '' })
const bfsForm = reactive({ product_batch: '', max_depth: 4 })

const EVENT_COLOR = {
  ISSUE_MATERIAL: '#f0a020',
  REPORT_PROGRESS: '#2b7cff',
  SCRAP: '#ec4c5a',
  INBOUND: '#27c281',
  FINISH: '#1a5cd8',
}

async function forward() {
  if (!fForm.product_batch) return
  forwardRows.value = (await forwardTrace(fForm.product_batch))?.events || []
}
async function backward() {
  if (!bForm.material_batch) return
  backwardRows.value = (await backwardTrace(bForm.material_batch))?.events || []
}
async function loadTree() {
  if (!fForm.product_batch) return
  tree.value = await traceTree(fForm.product_batch)
}
async function loadBfs() {
  if (!bfsForm.product_batch) return
  bfsTree.value = await traceBfs(bfsForm.product_batch, bfsForm.max_depth)
}
</script>

<template>
  <el-tabs>
    <el-tab-pane label="正向追溯：成品批次 → 物料/工单">
      <div class="toolbar">
        <el-input v-model="fForm.product_batch" placeholder="成品批次号" style="width: 240px" />
        <el-button type="primary" @click="forward">事件查询</el-button>
        <el-button @click="loadTree">追溯树</el-button>
      </div>

      <el-card v-if="tree" shadow="never" class="tree-card">
        <div class="tree-title">
          📦 成品批次
          <span class="mono">{{ tree.product_batch }}</span>
          · 关联工单 {{ tree.work_orders?.length || 0 }} 张
        </div>
        <div v-if="tree.work_orders?.length" class="tree-work-orders">
          <div v-for="w in tree.work_orders" :key="w.wo_id" class="tree-node">
            <el-tag type="primary" size="small">工单 {{ w.wo_no || w.wo_id }}</el-tag>
            <el-tag v-if="w.status" size="small" type="success">{{ w.status }}</el-tag>
            <span class="tree-events">
              {{ w.events?.map((e) => e.event_type).join(' → ') }}
            </span>
          </div>
        </div>
        <div v-else class="tree-empty">该批次暂无追溯事件</div>
      </el-card>

      <el-table v-if="forwardRows.length || (forwardRows && !tree)" :data="forwardRows" border style="margin-top: 16px">
        <el-table-column prop="wo_no" label="工单号" width="140" />
        <el-table-column prop="event_type" label="事件" width="140">
          <template #default="{ row }">
            <span :style="{ color: EVENT_COLOR[row.event_type] || '#1b2a40', fontWeight: 500 }">{{ row.event_type }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="material_code" label="物料" width="120" />
        <el-table-column prop="material_batch" label="物料批次" width="150" />
        <el-table-column prop="product_batch" label="成品批次" width="150" />
        <el-table-column prop="qty" label="数量" width="80" />
        <el-table-column prop="operator" label="操作人" width="100" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="明细">
          <template #default="{ row }">{{ row.detail ? JSON.stringify(row.detail) : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <el-tab-pane label="反向追溯 BFS：成品 → 原料 → 更上层">
      <div class="toolbar">
        <el-input v-model="bfsForm.product_batch" placeholder="成品批次号" style="width: 240px" />
        <span class="depth-label">最大深度</span>
        <el-input-number v-model="bfsForm.max_depth" :min="1" :max="10" :controls="false" style="width: 80px" />
        <el-button type="primary" @click="loadBfs">BFS 树形追溯</el-button>
      </div>

      <div v-if="bfsTree" class="bfs-container">
        <el-card shadow="never" class="bfs-card">
          <div class="tree-title">
            🌳 BFS 反向追溯 · 成品批次 <span class="mono">{{ bfsTree.product_batch }}</span>
            · 共 {{ bfsTree.total_nodes || bfsTree.layers?.length || 0 }} 层
          </div>
        </el-card>

        <div v-if="bfsTree.layers?.length" class="bfs-layers">
          <div
            v-for="(layer, li) in bfsTree.layers"
            :key="li"
            class="bfs-layer"
            :style="{ gridColumn: li + 1 }"
          >
            <div class="layer-header">
              <el-tag :type="li === 0 ? 'primary' : 'info'" size="small">第 {{ li + 1 }} 层</el-tag>
              <span class="layer-event">{{ layer.event_type || '-' }}</span>
            </div>
            <div class="layer-node">
              <div class="node-batch mono">{{ layer.batch_no }}</div>
              <div class="node-mat">{{ layer.material_code }} · {{ layer.material_name || '' }}</div>
              <div class="node-meta">
                <el-tag v-if="layer.wo_no" size="small" type="warning">工单 {{ layer.wo_no }}</el-tag>
                <span v-if="layer.qty" class="node-qty">数量 {{ layer.qty }}</span>
              </div>
            </div>
          </div>
        </div>

        <el-empty v-else description="无追溯数据" />
      </div>
    </el-tab-pane>

    <el-tab-pane label="反向追溯：物料批次 → 成品工单">
      <div class="toolbar">
        <el-input v-model="bForm.material_batch" placeholder="物料批次号" style="width: 240px" />
        <el-button type="primary" @click="backward">查询</el-button>
      </div>
      <el-table :data="backwardRows" border>
        <el-table-column prop="wo_no" label="工单号" width="140" />
        <el-table-column prop="product_code" label="产品" width="120" />
        <el-table-column prop="product_batch" label="成品批次" width="150" />
        <el-table-column prop="event_type" label="事件" width="140">
          <template #default="{ row }">
            <span :style="{ color: EVENT_COLOR[row.event_type] || '#1b2a40', fontWeight: 500 }">{{ row.event_type }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="qty" label="数量" width="80" />
        <el-table-column prop="operator" label="操作人" width="100" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="明细">
          <template #default="{ row }">{{ row.detail ? JSON.stringify(row.detail) : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-tab-pane>
  </el-tabs>
</template>

<style scoped>
.mono { font-family: Consolas, 'Courier New', monospace; font-weight: 600; color: #1a5cd8; }
.depth-label { color: #5a6d86; font-size: 13px; margin-left: 8px; }

.tree-card { margin-bottom: 16px; }
.tree-title { font-weight: 600; font-size: 14px; margin-bottom: 12px; }
.tree-work-orders { display: flex; flex-direction: column; gap: 10px; }
.tree-node {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; background: #f4f8ff; border-radius: 8px; border: 1px solid #d6e3ff;
}
.tree-events { color: #5a6d86; font-size: 13px; }
.tree-empty { color: #9aa7ba; padding: 20px; text-align: center; }

.bfs-container { margin-top: 16px; }
.bfs-card { margin-bottom: 16px; }
.bfs-layers {
  display: flex; flex-direction: column; gap: 14px;
}
.bfs-layer {
  background: #f4f8ff; border: 1px solid #d6e3ff; border-radius: 10px;
  padding: 14px 18px;
}
.layer-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.layer-event { color: #5a6d86; font-size: 13px; }
.node-batch { font-size: 15px; margin-bottom: 4px; }
.node-mat { color: #1b2a40; font-size: 13px; margin-bottom: 6px; }
.node-meta { display: flex; gap: 10px; align-items: center; }
.node-qty { font-size: 12px; color: #2b7cff; font-weight: 600; }
</style>
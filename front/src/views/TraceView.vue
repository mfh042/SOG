<script setup>
import { ref, reactive } from 'vue'
import { forwardTrace, backwardTrace, traceTree } from '@/api/production'

const forwardRows = ref([])
const backwardRows = ref([])
const tree = ref(null)
const fForm = reactive({ product_batch: '' })
const bForm = reactive({ material_batch: '' })

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
</script>

<template>
  <el-tabs>
    <el-tab-pane label="正向追溯：成品批次 → 物料/工单">
      <div class="toolbar">
        <el-input v-model="fForm.product_batch" placeholder="成品批次号" style="width: 240px" />
        <el-button type="primary" @click="forward">查询</el-button>
        <el-button @click="loadTree">追溯树</el-button>
      </div>
      <el-card v-if="tree" shadow="never" class="tree">
        <div class="tree-title">成品批次 {{ tree.product_batch }} · 关联工单 {{ tree.work_orders.length }} 张</div>
        <div v-for="w in tree.work_orders" :key="w.wo_id" class="tree-node">
          <el-tag type="primary">工单 {{ w.wo_id }}</el-tag>
          <span class="tree-events">
            事件 {{ w.events.length }} 条：{{ w.events.map((e) => e.event_type).join(' → ') }}
          </span>
        </div>
        <div v-if="!tree.work_orders.length" class="tree-empty">该批次暂无追溯事件</div>
      </el-card>
      <el-table :data="forwardRows" border>
        <el-table-column prop="wo_id" label="工单ID" width="90" />
        <el-table-column prop="event_type" label="事件" width="130" />
        <el-table-column prop="material_batch" label="物料批次" width="150" />
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column prop="operator" label="操作人" width="110" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="明细">
          <template #default="{ row }">{{ JSON.stringify(row.detail) }}</template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <el-tab-pane label="反向追溯：物料批次 → 成品工单">
      <div class="toolbar">
        <el-input v-model="bForm.material_batch" placeholder="物料批次号" style="width: 240px" />
        <el-button type="primary" @click="backward">查询</el-button>
      </div>
      <el-table :data="backwardRows" border>
        <el-table-column prop="wo_id" label="工单ID" width="90" />
        <el-table-column prop="product_batch" label="成品批次" width="150" />
        <el-table-column prop="event_type" label="事件" width="130" />
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column prop="operator" label="操作人" width="110" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="明细">
          <template #default="{ row }">{{ JSON.stringify(row.detail) }}</template>
        </el-table-column>
      </el-table>
    </el-tab-pane>
  </el-tabs>
</template>
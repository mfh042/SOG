<script setup>
const logs = [
  { time: '2026-11-16 10:32:18', user: 'admin', action: 'LOGIN', target: 'POST /api/auth/login', ip: '127.0.0.1' },
  { time: '2026-11-16 10:28:45', user: 'planner', action: 'CREATE', target: 'work_order WO-20261116-001', ip: '127.0.0.1' },
  { time: '2026-11-16 09:55:02', user: 'operator', action: 'REPORT', target: 'production_progress @ ST-01', ip: '127.0.0.1' },
  { time: '2026-11-16 09:30:11', user: 'quality', action: 'QC_PASS', target: 'quality_inspection QI-20261116-001', ip: '127.0.0.1' },
  { time: '2026-11-15 17:12:33', user: 'admin', action: 'UPDATE', target: 'app_user: station_code=ST-01', ip: '127.0.0.1' },
  { time: '2026-11-15 16:40:09', user: 'planner', action: 'KIT_CHECK', target: 'sales_order SO-20261115-001', ip: '127.0.0.1' },
]

const actionType = {
  LOGIN: 'primary', CREATE: 'success', UPDATE: 'warning', DELETE: 'danger',
  REPORT: 'info', QC_PASS: 'success', QC_FAIL: 'danger', KIT_CHECK: 'primary',
}
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-title">最近操作日志（演示数据）</div>
      <el-table :data="logs" stripe>
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column prop="user" label="操作人" width="120" />
        <el-table-column prop="action" label="动作" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="actionType[row.action] || 'info'">
              {{ row.action }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="对象" min-width="260" />
        <el-table-column prop="ip" label="IP 地址" width="140" />
      </el-table>
      <div class="hint">注：操作日志后端尚未落地（计划新建 operation_log 表 + 中间件拦截关键写操作），当前为前端演示数据。</div>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.card { background: #fff; border-radius: 10px; padding: 20px; border: 1px solid var(--border); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary); }
.hint { margin-top: 12px; font-size: 12px; color: var(--text-muted); }
</style>
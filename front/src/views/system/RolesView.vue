<script setup>
const roles = [
  { code: 'ADMIN', name: '系统管理员', desc: '拥有全部功能权限', color: '#f56c6c' },
  { code: 'MANAGER', name: '部门经理', desc: '生产 + 订单 + 看板全部只读与审批', color: '#e6a23c' },
  { code: 'PLANNER', name: '生产计划员', desc: '订单、BOM、工单创建与齐套检查', color: '#2b7cff' },
  { code: 'OPERATOR', name: '装配操作工', desc: '工位 SOP 查看、生产报工、质量自检', color: '#909399' },
  { code: 'QUALITY', name: '质检员', desc: '质量检验录入、不良代码字典维护、不合格品处置', color: '#67c23a' },
]

const permissions = [
  { module: '总览看板', admin: true, manager: true, planner: true, operator: true, quality: true },
  { module: '用户管理', admin: true, manager: true, planner: false, operator: false, quality: false },
  { module: '物料主数据', admin: true, manager: true, planner: true, operator: false, quality: false },
  { module: 'BOM 清单', admin: true, manager: true, planner: true, operator: false, quality: false },
  { module: '库存台账', admin: true, manager: true, planner: true, operator: false, quality: true },
  { module: '销售订单', admin: true, manager: true, planner: true, operator: false, quality: false },
  { module: '生产工单', admin: true, manager: true, planner: true, operator: true, quality: false },
  { module: '质量检验', admin: true, manager: true, planner: false, operator: true, quality: true },
  { module: '不良代码', admin: true, manager: true, planner: false, operator: false, quality: true },
  { module: 'SOP 作业指导', admin: true, manager: true, planner: true, operator: true, quality: false },
  { module: '批次追溯', admin: true, manager: true, planner: true, operator: false, quality: true },
]
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-title">角色定义</div>
      <div class="role-grid">
        <div v-for="r in roles" :key="r.code" class="role-card">
          <div class="role-badge" :style="{ background: r.color + '18', color: r.color, borderColor: r.color + '40' }">
            {{ r.code }}
          </div>
          <div class="role-name">{{ r.name }}</div>
          <div class="role-desc">{{ r.desc }}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">功能权限矩阵</div>
      <el-table :data="permissions" border stripe size="small">
        <el-table-column prop="module" label="功能模块" width="160" fixed />
        <el-table-column label="ADMIN" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.admin" color="#67c23a"><CircleCheckFilled /></el-icon>
            <el-icon v-else color="#c0c4cc"><CircleCloseFilled /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="MANAGER" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.manager" color="#67c23a"><CircleCheckFilled /></el-icon>
            <el-icon v-else color="#c0c4cc"><CircleCloseFilled /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="PLANNER" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.planner" color="#67c23a"><CircleCheckFilled /></el-icon>
            <el-icon v-else color="#c0c4cc"><CircleCloseFilled /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="OPERATOR" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.operator" color="#67c23a"><CircleCheckFilled /></el-icon>
            <el-icon v-else color="#c0c4cc"><CircleCloseFilled /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="QUALITY" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.quality" color="#67c23a"><CircleCheckFilled /></el-icon>
            <el-icon v-else color="#c0c4cc"><CircleCloseFilled /></el-icon>
          </template>
        </el-table-column>
      </el-table>
      <div class="hint">注：当前为规划矩阵，系统已落地 JWT 角色鉴权（header X-Role + payload role claim），按钮级权限待后续版本实现。</div>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.card { background: #fff; border-radius: 10px; padding: 20px; border: 1px solid var(--border); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary); }
.role-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.role-card { padding: 16px; border: 1px solid var(--border); border-radius: 10px; text-align: center; transition: box-shadow 0.2s; }
.role-card:hover { box-shadow: 0 4px 16px rgba(43, 124, 255, 0.12); }
.role-badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 12px; border: 1px solid; margin-bottom: 8px; }
.role-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.role-desc { font-size: 12px; color: var(--text-muted); line-height: 1.5; }
.hint { margin-top: 12px; font-size: 12px; color: var(--text-muted); }
</style>
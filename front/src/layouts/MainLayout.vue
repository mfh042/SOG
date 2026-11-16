<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
const menus = [
  { path: '/orders', label: '订单管理', icon: 'Document' },
  { path: '/materials', label: '物料主数据', icon: 'Box' },
  { path: '/inventory', label: '库存台账', icon: 'Goods' },
  { path: '/work-orders', label: '生产工单', icon: 'Setting' },
  { path: '/quality', label: '质量检验', icon: 'CircleCheck' },
  { path: '/trace', label: '批次追溯', icon: 'Connection' },
]
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">SOG 生产支援系统</div>
      <el-menu :default-active="route.path" router class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ route.meta.title }}</span>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout { height: 100%; }
.aside { background: #0f2a52; color: #fff; }
.logo { height: 56px; line-height: 56px; text-align: center; font-weight: 700; letter-spacing: 1px; }
.menu { background: transparent; border: none; }
.menu :deep(.el-menu-item) { color: #c9d8ee; }
.menu :deep(.el-menu-item.is-active) { background: #1d6ce0; color: #fff; }
.header {
  background: #fff; border-bottom: 1px solid #e6edf5;
  display: flex; align-items: center;
}
.main { background: var(--bg); }
</style>

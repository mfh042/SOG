<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menus = computed(() => [
  {
    label: '总览',
    icon: 'Monitor',
    key: 'overview',
    perm: 'dashboard:read',
    items: [
      { path: '/dashboard', label: '运营看板', perm: 'dashboard:read' },
    ],
  },
  {
    label: '系统管理',
    icon: 'Setting',
    key: 'system',
    perm: 'material:read',
    items: [
      { path: '/system/users', label: '用户管理', perm: 'material:read' },
      { path: '/system/roles', label: '角色授权', perm: 'material:read' },
      { path: '/system/logs', label: '审计日志', perm: 'admin:audit' },
    ],
  },
  {
    label: '主数据管理',
    icon: 'Collection',
    key: 'master',
    perm: 'material:read',
    items: [
      { path: '/materials', label: '物料主数据', perm: 'material:read' },
      { path: '/boms', label: 'BOM 清单', perm: 'bom:read' },
      { path: '/inspect-types', label: '检验类型字典', perm: 'quality:read' },
      { path: '/defect-codes', label: '不良代码字典', perm: 'defect:read' },
    ],
  },
  {
    label: '物资管理',
    icon: 'Box',
    key: 'material',
    perm: 'inventory:all',
    items: [
      { path: '/inventory/hub', label: '物料管理中心', perm: 'inventory:all' },
      { path: '/consumables/hub', label: '消耗品管理中心', perm: 'inventory:all' },
      { path: '/wip/hub', label: '在制品管理中心', perm: 'wip:read' },
      { path: '/stock/txn', label: '批次与流水', perm: 'inventory:all' },
    ],
  },
  {
    label: '生产订单',
    icon: 'Document',
    key: 'order',
    perm: 'orders:read',
    items: [
      { path: '/orders/work', label: '生产工单', perm: 'orders:read' },
      { path: '/orders/adjust', label: '订单调整', perm: 'orders:update' },
      { path: '/orders/release', label: '生产发布', perm: 'orders:update' },
    ],
  },
  {
    label: '生产管理',
    icon: 'Operation',
    key: 'production',
    perm: 'production:read',
    items: [
      { path: '/orders/monitor', label: '生产执行监控', perm: 'orders:read' },
      { path: '/quality', label: '质量检验', perm: 'quality:read' },
      { path: '/sops', label: 'SOP 作业指导', perm: 'sop:read' },
      { path: '/trace', label: '批次追溯', perm: 'trace:read' },
    ],
  },
  {
    label: '设备管理',
    icon: 'Cpu',
    key: 'device',
    perm: 'device:read',
    items: [
      { path: '/devices', label: '设备直连', perm: 'device:read' },
    ],
  },
].map(group => {
  const filtered = group.items.filter(it => auth.hasPerm(it.perm))
  if (filtered.length === 0) return null
  return { ...group, items: filtered }
}).filter(Boolean))

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="236px" class="aside">
      <div class="glow glow-1"></div>
      <div class="glow glow-2"></div>

      <div class="logo">
        <div class="logo-mark">
          <img src="/logo.jpg" alt="SOG" class="logo-img" />
        </div>
        <div class="logo-text-group">
          <div class="logo-text">生产作业支援系统</div>
          <div class="logo-sub">Smart Operation Guidance</div>
        </div>
      </div>

      <div class="menu-wrap">
        <el-menu
          :default-active="route.path"
          :default-openeds="menus.map(m => m.key)"
          router
          class="menu"
        >
          <template v-for="(group, gi) in menus" :key="gi">
            <el-sub-menu
              v-if="group.items.length > 1"
              :index="group.key"
            >
              <template #title>
                <span class="group-indicator"></span>
                <el-icon class="group-icon"><component :is="group.icon" /></el-icon>
                <span class="group-label">{{ group.label }}</span>
              </template>
              <template v-for="(it, ti) in group.items" :key="ti">
                <el-sub-menu
                  v-if="it.isSub"
                  :index="group.key + '-' + it.label"
                >
                  <template #title>
                    <span class="dot"></span>
                    <span>{{ it.label }}</span>
                  </template>
                  <el-menu-item v-for="sub in it.items" :key="sub.path" :index="sub.path">
                    <span class="dot"></span>
                    <span>{{ sub.label }}</span>
                  </el-menu-item>
                </el-sub-menu>
                <el-menu-item v-else :index="it.path">
                  <span class="dot"></span>
                  <span>{{ it.label }}</span>
                </el-menu-item>
              </template>
            </el-sub-menu>
            <el-menu-item
              v-else
              :index="group.items[0].path"
              class="standalone"
            >
              <span class="group-indicator"></span>
              <el-icon class="group-icon"><component :is="group.icon" /></el-icon>
              <span class="group-label">{{ group.items[0].label }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </div>

      <div class="aside-footer">
        <div class="status-dot"></div>
        <span>系统在线</span>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="page-title">{{ route.meta.title }}</div>
        <div class="header-right">
          <el-dropdown @command="handleLogout">
            <div class="user-chip">
              <div class="avatar">{{ (auth.user?.display_name || auth.user?.username || '?').charAt(0).toUpperCase() }}</div>
              <div class="user-info">
                <div class="user-name">{{ auth.user?.display_name || auth.user?.username || '未登录' }}</div>
                <div class="user-role">{{ auth.user?.role || '-' }}</div>
              </div>
              <el-icon class="chevron"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout { height: 100vh; }

.aside {
  position: relative;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(43, 124, 255, 0.15), transparent),
    linear-gradient(180deg, #0b1f3f 0%, #081631 50%, #061229 100%);
  color: #c9d8ee;
  border-right: 1px solid rgba(43, 124, 255, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.aside::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(43, 124, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(43, 124, 255, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}
.glow-1 {
  width: 180px; height: 180px;
  top: -40px; left: -40px;
  background: radial-gradient(circle, rgba(43, 124, 255, 0.35), transparent 70%);
}
.glow-2 {
  width: 140px; height: 140px;
  bottom: 100px; right: -30px;
  background: radial-gradient(circle, rgba(108, 166, 255, 0.2), transparent 70%);
}

.logo {
  position: relative;
  z-index: 1;
  padding: 22px 20px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(43, 124, 255, 0.12);
}
.logo-mark {
  position: relative;
  width: 42px; height: 42px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.logo-img {
  width: 40px; height: 40px;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  animation: logoFloat 4s ease-in-out infinite;
}
@keyframes logoFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}
.logo-text-group { line-height: 1.3; }
.logo-text { color: #eaf2ff; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; }
.logo-sub { color: rgba(108, 166, 255, 0.6); font-size: 10px; letter-spacing: 1px; font-family: monospace; }

.menu-wrap {
  position: relative;
  z-index: 1;
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
}
.menu-wrap::-webkit-scrollbar { width: 4px; }
.menu-wrap::-webkit-scrollbar-thumb { background: rgba(43, 124, 255, 0.2); border-radius: 2px; }

.menu {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

.menu :deep(.el-sub-menu__title),
.menu :deep(.el-menu-item) {
  position: relative;
  color: #8fa6c7;
  border-radius: 6px;
  height: 40px;
  line-height: 40px;
  margin-bottom: 2px;
  transition: all 0.25s ease;
  font-size: 13px;
}

.menu :deep(.el-sub-menu__title:hover),
.menu :deep(.el-menu-item:hover) {
  background: rgba(43, 124, 255, 0.08);
  color: #cfe0ff;
}

.menu :deep(.el-sub-menu__title:hover) .group-indicator,
.menu :deep(.el-menu-item:hover) .group-indicator {
  background: linear-gradient(180deg, #6ca6ff, #2b7cff);
  box-shadow: 0 0 8px rgba(43, 124, 255, 0.6);
  height: 16px;
}

.group-indicator {
  position: absolute;
  left: -2px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 10px;
  background: #1e3a6a;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.group-icon {
  font-size: 16px;
  margin-right: 10px;
  color: #5a7ba8;
  transition: color 0.25s;
}
.menu :deep(.el-sub-menu__title:hover .group-icon),
.menu :deep(.el-menu-item:hover .group-icon) {
  color: #6ca6ff;
}

.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(43, 124, 255, 0.25) 0%, rgba(43, 124, 255, 0.08) 100%) !important;
  color: #fff !important;
  box-shadow: inset 0 0 0 1px rgba(43, 124, 255, 0.2);
}
.menu :deep(.el-menu-item.is-active) .group-indicator {
  background: linear-gradient(180deg, #6ca6ff, #2b7cff);
  box-shadow: 0 0 10px rgba(43, 124, 255, 0.8);
  height: 22px;
}
.menu :deep(.el-menu-item.is-active) .group-icon {
  color: #6ca6ff;
}
.menu :deep(.el-menu-item.is-active)::after {
  content: '';
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px; height: 6px;
  background: #6ca6ff;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(108, 166, 255, 0.8);
}

.menu :deep(.el-sub-menu .el-menu) {
  background: rgba(6, 18, 41, 0.5) !important;
  border-radius: 6px;
  margin: 4px 0;
  padding: 4px 6px !important;
  border: 1px solid rgba(43, 124, 255, 0.06);
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.2);
}

.menu :deep(.el-sub-menu .el-sub-menu__title) {
  height: 34px;
  line-height: 34px;
  font-size: 12.5px;
  color: #7a92b5;
  padding-left: 16px !important;
  margin-bottom: 1px;
}
.menu :deep(.el-sub-menu .el-sub-menu__title:hover) {
  background: rgba(43, 124, 255, 0.1) !important;
  color: #cfe0ff !important;
}
.menu :deep(.el-sub-menu .el-sub-menu .el-menu) {
  background: rgba(4, 12, 30, 0.6) !important;
  margin: 2px 0;
  padding: 2px 4px !important;
  border: 1px solid rgba(43, 124, 255, 0.04);
}
.menu :deep(.el-sub-menu .el-sub-menu .el-menu-item) {
  padding-left: 30px !important;
  font-size: 12px;
  height: 32px;
  line-height: 32px;
}

.menu :deep(.el-sub-menu .el-menu-item) {
  padding-left: 36px !important;
  font-size: 12.5px;
  height: 34px;
  line-height: 34px;
  margin-bottom: 1px;
  color: #7a92b5;
  border-radius: 4px;
}

.menu :deep(.el-sub-menu .el-menu-item .dot) {
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px; height: 4px;
  border-radius: 50%;
  background: #2a4572;
  transition: all 0.25s;
}

.menu :deep(.el-sub-menu .el-menu-item:hover) {
  background: rgba(43, 124, 255, 0.1) !important;
  color: #cfe0ff !important;
}
.menu :deep(.el-sub-menu .el-menu-item:hover .dot) {
  background: #6ca6ff;
  box-shadow: 0 0 6px rgba(108, 166, 255, 0.7);
}

.menu :deep(.el-sub-menu .el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(43, 124, 255, 0.3), rgba(43, 124, 255, 0.05)) !important;
  color: #fff !important;
}
.menu :deep(.el-sub-menu .el-menu-item.is-active .dot) {
  background: #6ca6ff;
  box-shadow: 0 0 8px rgba(108, 166, 255, 0.9);
  width: 6px; height: 6px;
}
.menu :deep(.el-sub-menu .el-menu-item.is-active)::after {
  display: none;
}

.menu :deep(.el-sub-menu__icon-arrow) {
  color: #3d5a8a !important;
  font-size: 12px;
}
.menu :deep(.el-sub-menu.is-active > .el-sub-menu__title .el-sub-menu__icon-arrow) {
  color: #6ca6ff !important;
}

.aside-footer {
  position: relative;
  z-index: 1;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: rgba(108, 166, 255, 0.6);
  border-top: 1px solid rgba(43, 124, 255, 0.08);
  letter-spacing: 0.5px;
}
.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
  animation: blink 2s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header {
  background: #fff;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
}
.page-title { font-size: 16px; font-weight: 600; margin: 0; color: var(--text-primary); }
.header-right { display: flex; align-items: center; gap: 16px; }
.user-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px 6px 6px;
  border-radius: 22px;
  background: var(--brand-50);
  cursor: pointer;
  transition: background 0.2s;
}
.user-chip:hover { background: #d6e3ff; }
.avatar {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, var(--brand), var(--brand-light));
  border-radius: 50%;
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 13px;
}
.user-info { line-height: 1.2; }
.user-name { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.user-role { font-size: 11px; color: var(--text-muted); text-transform: uppercase; }
.chevron { color: var(--text-muted); font-size: 14px; }
.main { background: var(--bg); padding: 20px 24px; overflow-y: auto; }
</style>
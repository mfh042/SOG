import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { title: '登录', public: true } },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '运营看板', perm: 'dashboard:read' } },
      { path: 'system/users', name: 'system-users', component: () => import('@/views/system/UserView.vue'), meta: { title: '用户管理', perm: 'material:read' } },
      { path: 'system/roles', name: 'system-roles', component: () => import('@/views/system/RolesView.vue'), meta: { title: '角色授权', perm: 'material:read' } },
      { path: 'system/logs', name: 'system-logs', component: () => import('@/views/system/LogsView.vue'), meta: { title: '审计日志', perm: 'admin:audit' } },
      { path: 'system/integration', name: 'system-integration', component: () => import('@/views/system/IntegrationConfig.vue'), meta: { title: '集成配置', perm: 'admin:audit' } },
      { path: 'materials', name: 'materials', component: () => import('@/views/MaterialView.vue'), meta: { title: '物料主数据', perm: 'material:read' } },
      { path: 'boms', name: 'boms', component: () => import('@/views/BomView.vue'), meta: { title: 'BOM 清单', perm: 'bom:read' } },
      { path: 'inventory/hub', name: 'inventory-hub', component: () => import('@/views/inventory/InventoryHub.vue'), props: { stockType: 'MATERIAL' }, meta: { title: '物料管理中心', perm: 'inventory:all' } },
      { path: 'inventory', redirect: { path: '/inventory/hub', query: { tab: 'query' } } },
      { path: 'inventory/in', redirect: { path: '/inventory/hub', query: { tab: 'in' } } },
      { path: 'inventory/out', redirect: { path: '/inventory/hub', query: { tab: 'out' } } },
      { path: 'inventory/query', redirect: { path: '/inventory/hub', query: { tab: 'query' } } },
      { path: 'inventory/stocktake', redirect: { path: '/inventory/hub', query: { tab: 'stocktake' } } },
      { path: 'wip/hub', name: 'wip-hub', component: () => import('@/views/inventory/WipHub.vue'), meta: { title: '在制品管理中心', perm: 'wip:read' } },
      { path: 'wip', redirect: { path: '/wip/hub', query: { tab: 'dashboard' } } },
      { path: 'consumables/hub', name: 'consumables-hub', component: () => import('@/views/inventory/InventoryHub.vue'), props: { stockType: 'CONSUMABLE' }, meta: { title: '消耗品管理中心', perm: 'inventory:all' } },
      { path: 'stock/txn', name: 'stock-txn', component: () => import('@/views/inventory/StockTxnView.vue'), meta: { title: '批次与流水', perm: 'inventory:all' } },
      { path: 'orders/work', name: 'order-work', component: () => import('@/views/orders/OrderWorkView.vue'), meta: { title: '生产工单', perm: 'orders:read' } },
      { path: 'orders/adjust', name: 'order-adjust', component: () => import('@/views/orders/OrderAdjustView.vue'), meta: { title: '订单调整', perm: 'orders:update' } },
      { path: 'orders/release', name: 'order-release', component: () => import('@/views/orders/OrderWorkView.vue'), props: { focusRelease: true }, meta: { title: '生产发布', perm: 'orders:update' } },
      { path: 'orders/monitor', name: 'order-monitor', component: () => import('@/views/orders/OrderMonitorView.vue'), meta: { title: '生产执行监控', perm: 'orders:read' } },
      { path: 'orders', redirect: '/orders/work' },
      { path: 'work-orders', name: 'work-orders', component: () => import('@/views/WorkOrderView.vue'), meta: { title: '生产工单', perm: 'production:read' } },
      { path: 'quality', name: 'quality', component: () => import('@/views/QualityView.vue'), meta: { title: '质量检验', perm: 'quality:read' } },
      { path: 'inspect-types', name: 'inspect-types', component: () => import('@/views/InspectTypeView.vue'), meta: { title: '检验类型字典', perm: 'quality:read' } },
      { path: 'defect-codes', name: 'defect-codes', component: () => import('@/views/DefectCodeView.vue'), meta: { title: '不良代码字典', perm: 'defect:read' } },
      { path: 'sops', name: 'sops', component: () => import('@/views/SopView.vue'), meta: { title: 'SOP 作业指导', perm: 'sop:read' } },
      { path: 'trace', name: 'trace', component: () => import('@/views/TraceView.vue'), meta: { title: '批次追溯', perm: 'trace:read' } },
      { path: 'devices', name: 'devices', component: () => import('@/views/DeviceView.vue'), meta: { title: '设备直连', perm: 'device:read' } },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const token = localStorage.getItem('delv_sog_token')
  if (!token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  const auth = useAuthStore()
  if (!auth.user || !auth.user.role) {
    try { await auth.refreshUser() } catch { return { name: 'login', query: { redirect: to.fullPath } } }
  }
  if (to.meta.perm) {
    if (!auth.hasPerm(to.meta.perm)) {
      return { name: 'dashboard' }
    }
  }
})

export default router
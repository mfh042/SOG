import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { title: '登录', public: true } },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '运营看板' } },
      { path: 'system/users', name: 'system-users', component: () => import('@/views/system/UserView.vue'), meta: { title: '用户管理' } },
      { path: 'system/roles', name: 'system-roles', component: () => import('@/views/system/RolesView.vue'), meta: { title: '角色授权' } },
      { path: 'system/logs', name: 'system-logs', component: () => import('@/views/system/LogsView.vue'), meta: { title: '操作日志' } },
      { path: 'materials', name: 'materials', component: () => import('@/views/MaterialView.vue'), meta: { title: '物料主数据' } },
      { path: 'boms', name: 'boms', component: () => import('@/views/BomView.vue'), meta: { title: 'BOM 清单' } },
      { path: 'inventory/hub', name: 'inventory-hub', component: () => import('@/views/inventory/InventoryHub.vue'), props: { stockType: 'MATERIAL' }, meta: { title: '物料管理中心' } },
      { path: 'inventory', redirect: { path: '/inventory/hub', query: { tab: 'query' } } },
      { path: 'inventory/in', redirect: { path: '/inventory/hub', query: { tab: 'in' } } },
      { path: 'inventory/out', redirect: { path: '/inventory/hub', query: { tab: 'out' } } },
      { path: 'inventory/query', redirect: { path: '/inventory/hub', query: { tab: 'query' } } },
      { path: 'inventory/stocktake', redirect: { path: '/inventory/hub', query: { tab: 'stocktake' } } },
      { path: 'wip/hub', name: 'wip-hub', component: () => import('@/views/inventory/WipHub.vue'), meta: { title: '在制品管理中心' } },
      { path: 'wip', redirect: { path: '/wip/hub', query: { tab: 'dashboard' } } },
      { path: 'consumables/hub', name: 'consumables-hub', component: () => import('@/views/inventory/InventoryHub.vue'), props: { stockType: 'CONSUMABLE' }, meta: { title: '消耗品管理中心' } },
      { path: 'consumables/in', redirect: { path: '/consumables/hub', query: { tab: 'in' } } },
      { path: 'consumables/out', redirect: { path: '/consumables/hub', query: { tab: 'out' } } },
      { path: 'consumables/query', redirect: { path: '/consumables/hub', query: { tab: 'query' } } },
      { path: 'consumables/stocktake', redirect: { path: '/consumables/hub', query: { tab: 'stocktake' } } },
      { path: 'orders/work', name: 'order-work', component: () => import('@/views/orders/OrderWorkView.vue'), meta: { title: '生产工单' } },
      { path: 'orders/adjust', name: 'order-adjust', component: () => import('@/views/orders/OrderAdjustView.vue'), meta: { title: '订单调整' } },
      { path: 'orders/monitor', name: 'order-monitor', component: () => import('@/views/orders/OrderMonitorView.vue'), meta: { title: '生产订单监控' } },
      { path: 'orders', redirect: '/orders/work' },
      { path: 'work-orders', name: 'work-orders', component: () => import('@/views/WorkOrderView.vue'), meta: { title: '生产工单' } },
      { path: 'quality', name: 'quality', component: () => import('@/views/QualityView.vue'), meta: { title: '质量检验' } },
      { path: 'defect-codes', name: 'defect-codes', component: () => import('@/views/DefectCodeView.vue'), meta: { title: '不良代码字典' } },
      { path: 'sops', name: 'sops', component: () => import('@/views/SopView.vue'), meta: { title: 'SOP 作业指导' } },
      { path: 'trace', name: 'trace', component: () => import('@/views/TraceView.vue'), meta: { title: '批次追溯' } },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.meta.public) return true
  const token = localStorage.getItem('sog_token')
  if (!token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
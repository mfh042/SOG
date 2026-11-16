import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/orders',
    children: [
      { path: 'orders', name: 'orders', component: () => import('@/views/OrderView.vue'), meta: { title: '订单管理' } },
      { path: 'materials', name: 'materials', component: () => import('@/views/MaterialView.vue'), meta: { title: '物料主数据' } },
      { path: 'inventory', name: 'inventory', component: () => import('@/views/InventoryView.vue'), meta: { title: '库存台账' } },
      { path: 'work-orders', name: 'work-orders', component: () => import('@/views/WorkOrderView.vue'), meta: { title: '生产工单' } },
      { path: 'quality', name: 'quality', component: () => import('@/views/QualityView.vue'), meta: { title: '质量检验' } },
      { path: 'trace', name: 'trace', component: () => import('@/views/TraceView.vue'), meta: { title: '批次追溯' } },
    ],
  },
]

export default createRouter({ history: createWebHistory(), routes })

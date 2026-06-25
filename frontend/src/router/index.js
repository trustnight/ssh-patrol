import { createRouter, createWebHistory } from 'vue-router'

// 路由配置
const routes = [
  {
    path: '/',
    redirect: '/patrol'
  },
  {
    path: '/patrol',
    name: 'PatrolTaskList',
    component: () => import('@/views/PatrolTaskList.vue')
  },
  {
    path: '/patrol/:taskId',
    name: 'PatrolTaskDetail',
    component: () => import('@/views/PatrolTaskDetail.vue')
  },
  {
    path: '/ssh-terminal',
    name: 'SSHTerminal',
    component: () => import('@/views/SSHTerminal.vue')
  },
  {
    path: '/template-manage',
    name: 'TemplateManage',
    component: () => import('@/views/TemplateManage.vue')
  },
  {
    path: '/device-manage',
    name: 'DeviceManage',
    component: () => import('@/views/DeviceManage.vue')
  },
  {
    path: '/screenshot',
    name: 'Screenshot',
    component: () => import('@/views/Screenshot.vue')
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

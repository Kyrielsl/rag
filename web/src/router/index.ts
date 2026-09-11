import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '../layouts/AdminLayout.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
    {
      path: '/',
      component: AdminLayout,
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'documents', component: () => import('../views/Documents.vue') },
        { path: 'review', component: () => import('../views/ReviewQueue.vue') },
        { path: 'domains', component: () => import('../views/Domains.vue') },
        { path: 'api-keys', component: () => import('../views/ApiKeys.vue') },
        { path: 'audit', component: () => import('../views/Audit.vue') }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.token) return '/login'
  if (to.path === '/login' && auth.token) return '/dashboard'
})

export default router
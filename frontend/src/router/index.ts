import type { Component } from 'vue'
import { createRouter, createWebHistory, RouteRecordRaw, NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import {
  BarChart2,
  BookOpen,
  Calculator,
  ClipboardList,
  History,
  LayoutDashboard,
  ShoppingBag,
  Target,
  User,
  Utensils,
} from 'lucide-vue-next'
import { useAuthStore } from '../store/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    icon?: Component
    title?: string
    showInSidebar?: boolean
  }
}

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('../views/ForgotPasswordView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('../views/ResetPasswordView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/confirm-deletion',
    name: 'confirm-deletion',
    component: () => import('../views/ConfirmDeletionView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true, icon: LayoutDashboard, title: 'Dashboard', showInSidebar: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/ProfileView.vue'),
    meta: { requiresAuth: true, icon: User, title: 'Profile', showInSidebar: true }
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('../views/ProductsView.vue'),
    meta: { requiresAuth: true, icon: ShoppingBag, title: 'Products', showInSidebar: true }
  },
  {
    path: '/products/:id',
    name: 'product-detail',
    component: () => import('../views/ProductDetailView.vue'),
    meta: { requiresAuth: true, icon: ShoppingBag, title: 'Products', showInSidebar: false }
  },
  {
    path: '/consume',
    name: 'consume',
    component: () => import('../views/ConsumeView.vue'),
    meta: { requiresAuth: true, icon: Utensils, title: 'Consume Daily Plan', showInSidebar: false }
  },
  {
    path: '/recipe-nutrients',
    name: 'recipe-nutrients',
    component: () => import('../views/RecipeNutrientsView.vue'),
    meta: { requiresAuth: true, icon: Calculator, title: 'Recipe Nutrients Calculator', showInSidebar: false }
  },
  {
    path: '/recipes',
    name: 'recipes',
    component: () => import('../views/RecipesView.vue'),
    meta: { requiresAuth: true, icon: BookOpen, title: 'Recipes', showInSidebar: true }
  },
  {
    path: '/recipes/:id',
    name: 'recipe-detail',
    component: () => import('../views/RecipeDetailView.vue'),
    meta: { requiresAuth: true, icon: BookOpen, title: 'Recipes', showInSidebar: false }
  },
  {
    path: '/history-import',
    name: 'history-import',
    component: () => import('../views/HistoryImportView.vue'),
    meta: { requiresAuth: true, icon: History, title: 'History', showInSidebar: true }
  },
  {
    path: '/consumption-history',
    name: 'consumption-history',
    component: () => import('../views/ConsumptionHistoryView.vue'),
    meta: { requiresAuth: true, icon: ClipboardList, title: 'Consumption Log', showInSidebar: true }
  },
  {
    path: '/consumed-stats',
    name: 'consumed-stats',
    component: () => import('../views/ConsumedProductsStatsView.vue'),
    meta: { requiresAuth: true, icon: BarChart2, title: 'Nutrient Stats', showInSidebar: true }
  },
  {
    path: '/daily-nutrition-limits',
    name: 'daily-nutrition-limits',
    component: () => import('../views/DailyNutritionLimitsView.vue'),
    meta: { requiresAuth: true, icon: Target, title: 'Daily Limits', showInSidebar: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard — awaits bootstrap so isAuthenticated is meaningful on first nav.
router.beforeEach(async (to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth === true

  if (authStore.bootstrapPromise) {
    await authStore.bootstrapPromise
  }

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (!requiresAuth && authStore.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router

import { createRouter, createWebHistory, RouteRecordRaw, NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '../store/auth'

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
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('../views/ProductsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/products/:id',
    name: 'product-detail',
    component: () => import('../views/ProductDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/consume',
    name: 'consume',
    component: () => import('../views/ConsumeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/recipe-nutrients',
    name: 'recipe-nutrients',
    component: () => import('../views/RecipeNutrientsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/recipes',
    name: 'recipes',
    component: () => import('../views/RecipesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/recipes/:id',
    name: 'recipe-detail',
    component: () => import('../views/RecipeDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history-import',
    name: 'history-import',
    component: () => import('../views/HistoryImportView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/consumption-history',
    name: 'consumption-history',
    component: () => import('../views/ConsumptionHistoryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/consumed-stats',
    name: 'consumed-stats',
    component: () => import('../views/ConsumedProductsStatsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/daily-nutrition-limits',
    name: 'daily-nutrition-limits',
    component: () => import('../views/DailyNutritionLimitsView.vue'),
    meta: { requiresAuth: true }
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
  const requiresAuth = to.meta.requiresAuth as boolean

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
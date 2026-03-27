import { createRouter, createWebHistory, RouteRecordRaw, NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '../store/auth'

// Views
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardView from '../views/DashboardView.vue'
import ProfileView from '../views/ProfileView.vue'
import ProductsView from '../views/ProductsView.vue'
import ConsumeView from '../views/ConsumeView.vue'
import RecipeNutrientsView from '../views/RecipeNutrientsView.vue'
import RecipesView from '../views/RecipesView.vue'
import ProductDetailView from '../views/ProductDetailView.vue'
import RecipeDetailView from '../views/RecipeDetailView.vue'
import HistoryImportView from '../views/HistoryImportView.vue'
import ConsumptionHistoryView from '../views/ConsumptionHistoryView.vue'
import ConsumedProductsStatsView from '../views/ConsumedProductsStatsView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import ConfirmDeletionView from '../views/ConfirmDeletionView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import DailyNutritionLimitsView from '../views/DailyNutritionLimitsView.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: { requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: ForgotPasswordView,
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: ResetPasswordView,
    meta: { requiresAuth: false }
  },
  {
    path: '/confirm-deletion',
    name: 'confirm-deletion',
    component: ConfirmDeletionView,
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: ProfileView,
    meta: { requiresAuth: true }
  },
  {
    path: '/products',
    name: 'products',
    component: ProductsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/products/:id',
    name: 'product-detail',
    component: ProductDetailView,
    meta: { requiresAuth: true }
  },
  {
    path: '/consume',
    name: 'consume',
    component: ConsumeView,
    meta: { requiresAuth: true }
  },
  {
    path: '/recipe-nutrients',
    name: 'recipe-nutrients',
    component: RecipeNutrientsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/recipes',
    name: 'recipes',
    component: RecipesView,
    meta: { requiresAuth: true }
  },
  {
    path: '/recipes/:id',
    name: 'recipe-detail',
    component: RecipeDetailView,
    meta: { requiresAuth: true }
  },
  {
    path: '/history-import',
    name: 'history-import',
    component: HistoryImportView,
    meta: { requiresAuth: true }
  },
  {
    path: '/consumption-history',
    name: 'consumption-history',
    component: ConsumptionHistoryView,
    meta: { requiresAuth: true }
  },
  {
    path: '/consumed-stats',
    name: 'consumed-stats',
    component: ConsumedProductsStatsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/daily-nutrition-limits',
    name: 'daily-nutrition-limits',
    component: DailyNutritionLimitsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFoundView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth as boolean
  
  // If route requires auth and user is not authenticated
  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } 
  // If route is login/register and user is already authenticated
  else if (!requiresAuth && authStore.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
    next('/dashboard')
  } 
  // Otherwise proceed as normal
  else {
    next()
  }
})

export default router 
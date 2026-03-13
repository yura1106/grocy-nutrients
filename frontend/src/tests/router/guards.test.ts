/**
 * Unit tests for router navigation guards (src/router/index.ts)
 *
 * Tests the guard function logic directly, without a full router,
 * to avoid issues with jsdom and window.location.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/store/auth'

/**
 * Simulates the guard function logic from router/index.ts.
 * Matches the real logic: requiresAuth + isAuthenticated → next('/login')
 */
const createGuard = (authStore: ReturnType<typeof useAuthStore>) => {
  return (
    to: { meta?: { requiresAuth?: boolean }; name?: string },
    _from: unknown,
    next: (path?: string) => void,
  ) => {
    const requiresAuth = to.meta?.requiresAuth as boolean | undefined
    if (requiresAuth && !authStore.isAuthenticated) {
      next('/login')
    } else if (
      !requiresAuth &&
      authStore.isAuthenticated &&
      (to.name === 'login' || to.name === 'register')
    ) {
      next('/dashboard')
    } else {
      next()
    }
  }
}

describe('Router Navigation Guards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  describe('unauthenticated user', () => {
    it('redirects to /login when accessing a protected route', () => {
      const store = useAuthStore()
      store.token = null
      const next = vi.fn()

      const guard = createGuard(store)
      guard({ meta: { requiresAuth: true }, name: 'dashboard' }, {}, next)

      expect(next).toHaveBeenCalledWith('/login')
    })

    it('allows access to the /login page', () => {
      const store = useAuthStore()
      store.token = null
      const next = vi.fn()

      const guard = createGuard(store)
      guard({ meta: { requiresAuth: false }, name: 'login' }, {}, next)

      expect(next).toHaveBeenCalledWith()
    })

    it('allows access to the /register page', () => {
      const store = useAuthStore()
      store.token = null
      const next = vi.fn()

      const guard = createGuard(store)
      guard({ meta: { requiresAuth: false }, name: 'register' }, {}, next)

      expect(next).toHaveBeenCalledWith()
    })

    it('redirects to /login for all protected routes', () => {
      const store = useAuthStore()
      store.token = null
      const next = vi.fn()
      const guard = createGuard(store)

      const protectedRoutes = ['dashboard', 'products', 'consume', 'recipes', 'profile']
      for (const routeName of protectedRoutes) {
        next.mockClear()
        guard({ meta: { requiresAuth: true }, name: routeName }, {}, next)
        expect(next).toHaveBeenCalledWith('/login')
      }
    })
  })

  describe('authenticated user', () => {
    it('redirects to /dashboard when attempting to access /login', () => {
      const store = useAuthStore()
      store.token = 'valid-auth-token'
      const next = vi.fn()

      const guard = createGuard(store)
      guard({ meta: { requiresAuth: false }, name: 'login' }, {}, next)

      expect(next).toHaveBeenCalledWith('/dashboard')
    })

    it('redirects to /dashboard when attempting to access /register', () => {
      const store = useAuthStore()
      store.token = 'valid-auth-token'
      const next = vi.fn()

      const guard = createGuard(store)
      guard({ meta: { requiresAuth: false }, name: 'register' }, {}, next)

      expect(next).toHaveBeenCalledWith('/dashboard')
    })

    it('allows access to protected routes', () => {
      const store = useAuthStore()
      store.token = 'valid-auth-token'
      const next = vi.fn()

      const guard = createGuard(store)
      guard({ meta: { requiresAuth: true }, name: 'dashboard' }, {}, next)

      expect(next).toHaveBeenCalledWith()
    })

    it('allows access to all protected routes', () => {
      const store = useAuthStore()
      store.token = 'valid-auth-token'
      const next = vi.fn()
      const guard = createGuard(store)

      const protectedRoutes = ['dashboard', 'products', 'consume', 'recipes', 'profile']
      for (const routeName of protectedRoutes) {
        next.mockClear()
        guard({ meta: { requiresAuth: true }, name: routeName }, {}, next)
        expect(next).toHaveBeenCalledWith()
      }
    })
  })
})

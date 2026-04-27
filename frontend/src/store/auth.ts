import { defineStore } from 'pinia'
import axios from 'axios'

axios.defaults.withCredentials = true

interface User {
  id: number
  username: string
  email: string
}

interface AuthState {
  user: User | null
  bootstrapping: boolean
  bootstrapPromise: Promise<void> | null
  bootstrapError: Error | null
}

const SESSION_USER_KEY = 'auth.user'

let isRefreshing = false
let failedQueue: Array<{ resolve: (value: unknown) => void; reject: (err: unknown) => void }> = []

function processQueue(error: unknown) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(null)
  })
  failedQueue = []
}

function readCachedUser(): User | null {
  try {
    const raw = sessionStorage.getItem(SESSION_USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

function cacheUser(user: User | null) {
  if (user) sessionStorage.setItem(SESSION_USER_KEY, JSON.stringify(user))
  else sessionStorage.removeItem(SESSION_USER_KEY)
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: readCachedUser(),
    bootstrapping: false,
    bootstrapPromise: null,
    bootstrapError: null,
  }),

  getters: {
    isAuthenticated(): boolean {
      return !!this.user
    },
  },

  actions: {
    async register(username: string, email: string, password: string) {
      await axios.post('/api/auth/register', { username, email, password })
      return true
    },

    async login(username: string, password: string) {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      await axios.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      // Login sets HttpOnly cookies and returns 204. Now load the user via /me.
      await this.fetchUser()
      return true
    },

    async fetchUser() {
      const response = await axios.get('/api/users/me')
      this.user = response.data
      cacheUser(this.user)
      return this.user
    },

    async updateProfile(data: { username?: string; email?: string; password?: string }) {
      const response = await axios.put('/api/users/me', data)
      if (this.user) {
        this.user.username = response.data.username
        this.user.email = response.data.email
        cacheUser(this.user)
      }
      return response.data
    },

    async requestAccountDeletion(exportData: boolean = false) {
      const params = exportData ? '?export_data=true' : ''
      const res = await axios.post(`/api/users/me/request-deletion${params}`)
      return res.data
    },

    async refreshAccessToken(): Promise<boolean> {
      try {
        await axios.post('/api/auth/refresh')
        return true
      } catch {
        // Refresh failed (token expired/revoked) — drop session, force re-login.
        this.user = null
        cacheUser(null)
        return false
      }
    },

    async logout() {
      try {
        await axios.post('/api/auth/logout')
      } catch (error) {
        console.error('Logout error:', error)
      } finally {
        this.user = null
        cacheUser(null)
      }
    },

    async logoutAllDevices() {
      try {
        await axios.post('/api/auth/logout-all')
      } catch (error) {
        console.error('Logout-all error:', error)
      } finally {
        this.user = null
        cacheUser(null)
      }
    },

    /**
     * Bootstrap session on app start. Idempotent — returns the same promise
     * across calls. Optimistically uses sessionStorage cache, then validates
     * with /me. 401 → clear; network error → keep optimistic, set bootstrapError.
     */
    bootstrap(): Promise<void> {
      if (this.bootstrapPromise) return this.bootstrapPromise
      this.bootstrapping = true
      this.bootstrapError = null
      this.bootstrapPromise = (async () => {
        try {
          const response = await axios.get('/api/users/me')
          this.user = response.data
          cacheUser(this.user)
        } catch (error: unknown) {
          const status = (error as { response?: { status?: number } })?.response?.status
          if (status === 401) {
            this.user = null
            cacheUser(null)
          } else {
            this.bootstrapError = error as Error
            // keep optimistic user if any — let UI render in degraded mode
          }
        } finally {
          this.bootstrapping = false
        }
      })()
      return this.bootstrapPromise
    },

    /**
     * Install the axios refresh-on-401 interceptor. Must be called once at app
     * startup (from main.ts).
     */
    installInterceptors() {
      axios.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config
          const url: string | undefined = originalRequest?.url
          const requestStatus = error.response?.status

          // 401 on /api/auth/refresh itself — abandon, do NOT retry.
          if (requestStatus === 401 && url?.includes('/api/auth/refresh')) {
            this.user = null
            cacheUser(null)
            return Promise.reject(error)
          }

          // 401 on any other endpoint — try refresh, retry once.
          if (
            requestStatus === 401 &&
            !originalRequest._retry &&
            !url?.includes('/api/auth/login') &&
            !url?.includes('/api/auth/register')
          ) {
            if (isRefreshing) {
              return new Promise((resolve, reject) => {
                failedQueue.push({
                  resolve: () => resolve(axios(originalRequest)),
                  reject,
                })
              })
            }

            originalRequest._retry = true
            isRefreshing = true

            const ok = await this.refreshAccessToken()
            isRefreshing = false

            if (ok) {
              processQueue(null)
              return axios(originalRequest)
            } else {
              processQueue(error)
              return Promise.reject(error)
            }
          }

          return Promise.reject(error)
        },
      )
    },
  },
})

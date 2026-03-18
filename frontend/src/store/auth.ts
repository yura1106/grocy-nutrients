import { defineStore } from 'pinia'
import axios from 'axios'

// Configure axios defaults
axios.defaults.withCredentials = true

interface User {
  id: number
  username: string
  email: string
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
}

let isRefreshing = false
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token)
    else reject(error)
  })
  failedQueue = []
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token'),
    refreshToken: localStorage.getItem('refreshToken'),
    user: null
  }),

  getters: {
    isAuthenticated(): boolean {
      return !!this.token
    }
  },

  actions: {
    async register(username: string, email: string, password: string) {
      try {
        await axios.post('/api/auth/register', {
          username,
          email,
          password
        })
        return true
      } catch (error) {
        console.error('Registration error:', error)
        throw error
      }
    },

    async login(username: string, password: string) {
      try {
        // FormData is required for OAuth2 password flow
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)

        const response = await axios.post('/api/auth/login', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        const { access_token, refresh_token } = response.data

        // Store tokens in localStorage and state
        localStorage.setItem('token', access_token)
        localStorage.setItem('refreshToken', refresh_token)
        this.token = access_token
        this.refreshToken = refresh_token

        // Set default Authorization header for future requests
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

        // Fetch user data
        await this.fetchUser()

        return true
      } catch (error) {
        console.error('Login error:', error)
        throw error
      }
    },

    async updateProfile(data: { username?: string; email?: string; password?: string }) {
      const response = await axios.put('/api/users/me', data)
      if (this.user) {
        this.user.username = response.data.username
        this.user.email = response.data.email
      }
      return response.data
    },

    async requestAccountDeletion(exportData: boolean = false) {
      const params = exportData ? '?export_data=true' : ''
      const res = await axios.post(`/api/users/me/request-deletion${params}`)
      return res.data
    },

    async fetchUser() {
      try {
        if (!this.token) {
          throw new Error('No token available')
        }
        const response = await axios.get('/api/users/me', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        this.user = response.data
        return this.user
      } catch (error) {
        console.error('Fetch user error:', error)
        this.logout()
        throw error
      }
    },

    async refreshAccessToken(): Promise<string | null> {
      if (!this.refreshToken) return null

      try {
        const response = await axios.post('/api/auth/refresh', {
          refresh_token: this.refreshToken
        })
        const { access_token, refresh_token } = response.data

        localStorage.setItem('token', access_token)
        localStorage.setItem('refreshToken', refresh_token)
        this.token = access_token
        this.refreshToken = refresh_token
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

        return access_token
      } catch {
        this.logout()
        return null
      }
    },

    async logout() {
      try {
        if (this.token) {
          // Call logout endpoint with the token
          await axios.post('/api/auth/logout', null, {
            headers: {
              'Authorization': `Bearer ${this.token}`
            }
          })
        }
      } catch (error) {
        console.error('Logout error:', error)
      } finally {
        // Always clear local state regardless of server response
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
        this.token = null
        this.refreshToken = null
        this.user = null
        delete axios.defaults.headers.common['Authorization']
      }
    },

    // Initialize auth from stored token
    init() {
      const token = localStorage.getItem('token')
      const refreshToken = localStorage.getItem('refreshToken')
      if (token) {
        this.token = token
        this.refreshToken = refreshToken
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
        this.fetchUser().catch(() => this.logout())
      }

      // Set up axios interceptor for automatic token refresh
      axios.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config

          if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.url?.includes('/api/auth/')
          ) {
            if (isRefreshing) {
              return new Promise((resolve, reject) => {
                failedQueue.push({
                  resolve: (token: string) => {
                    originalRequest.headers['Authorization'] = `Bearer ${token}`
                    resolve(axios(originalRequest))
                  },
                  reject,
                })
              })
            }

            originalRequest._retry = true
            isRefreshing = true

            const newToken = await this.refreshAccessToken()
            isRefreshing = false

            if (newToken) {
              processQueue(null, newToken)
              originalRequest.headers['Authorization'] = `Bearer ${newToken}`
              return axios(originalRequest)
            } else {
              processQueue(error, null)
              return Promise.reject(error)
            }
          }

          return Promise.reject(error)
        }
      )
    }
  }
})

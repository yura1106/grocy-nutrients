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
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token'),
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
        const { access_token } = response.data
        
        // Store token in localStorage and state
        localStorage.setItem('token', access_token)
        this.token = access_token
        
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
        this.token = null
        this.user = null
        delete axios.defaults.headers.common['Authorization']
      }
    },
    
    // Initialize auth from stored token
    init() {
      const token = localStorage.getItem('token')
      if (token) {
        this.token = token
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
        this.fetchUser().catch(() => this.logout())
      }
    }
  }
}) 
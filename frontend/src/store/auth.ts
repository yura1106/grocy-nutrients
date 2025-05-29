import { defineStore } from 'pinia'
import axios from 'axios'

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
        
        const response = await axios.post('/api/auth/login', formData)
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
        const response = await axios.get('/api/users/me')
        this.user = response.data
        return this.user
      } catch (error) {
        console.error('Fetch user error:', error)
        throw error
      }
    },
    
    async logout() {
      try {
        // Call logout endpoint (even though JWT can't be invalidated server-side)
        await axios.post('/api/auth/logout')
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
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        this.fetchUser().catch(() => this.logout())
      }
    }
  }
}) 
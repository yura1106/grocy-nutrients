/**
 * Unit tests for src/store/auth.ts
 *
 * Tests for the Pinia auth store:
 * - initial state
 * - isAuthenticated getter
 * - actions: login, logout, fetchUser, register, init
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/store/auth'
import axios from 'axios'

// Mock axios at the module level
vi.mock('axios', () => {
  const mockAxios = {
    post: vi.fn(),
    get: vi.fn(),
    defaults: {
      withCredentials: false,
      headers: {
        common: {} as Record<string, string>,
      },
    },
  }
  return { default: mockAxios }
})

const mockedAxios = vi.mocked(axios, true)

describe('Auth Store', () => {
  beforeEach(() => {
    // Fresh Pinia for each test
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    // Clear the Authorization header
    delete (axios.defaults.headers.common as Record<string, string>)['Authorization']
  })

  describe('initial state', () => {
    it('has null token when localStorage is empty', () => {
      const store = useAuthStore()
      expect(store.token).toBeNull()
    })

    it('loads token from localStorage on initialization', () => {
      localStorage.setItem('token', 'stored-token-value')
      const store = useAuthStore()
      expect(store.token).toBe('stored-token-value')
    })

    it('has null user on startup', () => {
      const store = useAuthStore()
      expect(store.user).toBeNull()
    })
  })

  describe('isAuthenticated getter', () => {
    it('returns false when token is null', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('returns true when token is set', () => {
      const store = useAuthStore()
      store.token = 'some-valid-token'
      expect(store.isAuthenticated).toBe(true)
    })

    it('returns false for empty string token', () => {
      const store = useAuthStore()
      store.token = ''
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('login action', () => {
    it('stores token in state and localStorage after successful login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({
        data: { access_token: 'new-auth-token', token_type: 'bearer' },
      })
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 1, username: 'testuser', email: 'test@example.com' },
      })

      await store.login('testuser', 'password123')

      expect(store.token).toBe('new-auth-token')
      expect(localStorage.getItem('token')).toBe('new-auth-token')
    })

    it('sets Authorization header after login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({
        data: { access_token: 'header-test-token', token_type: 'bearer' },
      })
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 1, username: 'u', email: 'e@e.com' },
      })

      await store.login('user', 'pass')

      expect(axios.defaults.headers.common['Authorization']).toBe('Bearer header-test-token')
    })

    it('calls fetchUser after successful login', async () => {
      const store = useAuthStore()
      const fetchUserSpy = vi.spyOn(store, 'fetchUser').mockResolvedValue({ id: 1, username: 'u', email: 'e@e.com' })
      mockedAxios.post.mockResolvedValueOnce({
        data: { access_token: 'token', token_type: 'bearer' },
      })

      await store.login('user', 'pass')

      expect(fetchUserSpy).toHaveBeenCalledOnce()
    })

    it('returns true after successful login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({
        data: { access_token: 'token', token_type: 'bearer' },
      })
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 1, username: 'u', email: 'e@e.com' },
      })

      const result = await store.login('user', 'pass')
      expect(result).toBe(true)
    })

    it('throws an error on failed login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'))

      await expect(store.login('user', 'wrong')).rejects.toThrow()
    })

    it('does not set token after failed login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockRejectedValueOnce(new Error('Unauthorized'))

      try {
        await store.login('user', 'wrong')
      } catch {
        // expect an error
      }

      expect(store.token).toBeNull()
    })
  })

  describe('logout action', () => {
    it('clears token from state and localStorage', async () => {
      const store = useAuthStore()
      store.token = 'existing-token'
      localStorage.setItem('token', 'existing-token')
      mockedAxios.post.mockResolvedValueOnce({ data: { message: 'ok' } })

      await store.logout()

      expect(store.token).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
    })

    it('clears user after logout', async () => {
      const store = useAuthStore()
      store.token = 'token'
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      mockedAxios.post.mockResolvedValueOnce({ data: {} })

      await store.logout()

      expect(store.user).toBeNull()
    })

    it('clears state even if the logout API call fails', async () => {
      const store = useAuthStore()
      store.token = 'token'
      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'))

      await store.logout()

      expect(store.token).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
    })

    it('removes the Authorization header', async () => {
      const store = useAuthStore()
      store.token = 'token'
      axios.defaults.headers.common['Authorization'] = 'Bearer token'
      mockedAxios.post.mockResolvedValueOnce({ data: {} })

      await store.logout()

      expect(axios.defaults.headers.common['Authorization']).toBeUndefined()
    })

    it('does not throw when token is absent', async () => {
      const store = useAuthStore()
      store.token = null

      await expect(store.logout()).resolves.toBeUndefined()
    })
  })

  describe('fetchUser action', () => {
    it('sets user after successful request', async () => {
      const store = useAuthStore()
      store.token = 'valid-token'
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 5, username: 'fetched', email: 'fetched@example.com' },
      })

      await store.fetchUser()

      expect(store.user).toEqual({ id: 5, username: 'fetched', email: 'fetched@example.com' })
    })

    it('throws an error when token is absent', async () => {
      const store = useAuthStore()
      store.token = null
      // Mock logout to avoid recursive call
      vi.spyOn(store, 'logout').mockResolvedValue(undefined)

      await expect(store.fetchUser()).rejects.toThrow('No token available')
    })

    it('calls logout on failed request', async () => {
      const store = useAuthStore()
      store.token = 'bad-token'
      mockedAxios.get.mockRejectedValueOnce(new Error('401 Unauthorized'))
      const logoutSpy = vi.spyOn(store, 'logout').mockResolvedValue(undefined)

      await expect(store.fetchUser()).rejects.toThrow()
      expect(logoutSpy).toHaveBeenCalledOnce()
    })

    it('returns user object on success', async () => {
      const store = useAuthStore()
      store.token = 'valid-token'
      const userData = { id: 3, username: 'user3', email: '3@test.com' }
      mockedAxios.get.mockResolvedValueOnce({ data: userData })

      const result = await store.fetchUser()
      expect(result).toEqual(userData)
    })
  })

  describe('register action', () => {
    it('calls API with correct data and returns true', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({ data: { id: 1 } })

      const result = await store.register('newuser', 'new@example.com', 'password123')

      expect(result).toBe(true)
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/auth/register',
        expect.objectContaining({
          username: 'newuser',
          email: 'new@example.com',
          password: 'password123',
        }),
      )
    })

    it('throws an error on failed registration', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockRejectedValueOnce({
        response: { data: { detail: 'Email already taken' } },
      })

      await expect(
        store.register('user', 'taken@example.com', 'pass'),
      ).rejects.toBeDefined()
    })
  })

  describe('init action', () => {
    it('loads token and sets Authorization header', async () => {
      localStorage.setItem('token', 'init-token')
      const store = useAuthStore()
      // Mock fetchUser to avoid a real request
      const fetchSpy = vi.spyOn(store, 'fetchUser').mockResolvedValue({ id: 1, username: 'u', email: 'e@e.com' })

      store.init()

      expect(store.token).toBe('init-token')
      expect(axios.defaults.headers.common['Authorization']).toBe('Bearer init-token')
      expect(fetchSpy).toHaveBeenCalledOnce()
    })

    it('does not call fetchUser when localStorage is empty', () => {
      localStorage.clear()
      const store = useAuthStore()
      const fetchSpy = vi.spyOn(store, 'fetchUser').mockResolvedValue({ id: 1, username: 'u', email: 'e@e.com' })

      store.init()

      expect(fetchSpy).not.toHaveBeenCalled()
    })
  })
})

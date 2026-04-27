/**
 * Unit tests for src/store/auth.ts
 *
 * Pinia auth store, cookie-based session.
 * Tokens live in HttpOnly cookies — JS never sees them. Tests verify state
 * (this.user) and HTTP shape (axios calls), not cookie internals.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/store/auth'
import axios from 'axios'

vi.mock('axios', () => {
  const mockAxios = {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    defaults: {
      withCredentials: false,
      headers: {
        common: {} as Record<string, string>,
      },
    },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }
  return { default: mockAxios }
})

const mockedAxios = vi.mocked(axios, true)

describe('Auth Store (cookie session)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('has null user when sessionStorage is empty', () => {
      const store = useAuthStore()
      expect(store.user).toBeNull()
    })

    it('hydrates user from sessionStorage on initialization', () => {
      sessionStorage.setItem(
        'auth.user',
        JSON.stringify({ id: 7, username: 'cached', email: 'c@c.com' }),
      )
      const store = useAuthStore()
      expect(store.user).toEqual({ id: 7, username: 'cached', email: 'c@c.com' })
    })

    it('survives a malformed sessionStorage value', () => {
      sessionStorage.setItem('auth.user', '{not-json')
      const store = useAuthStore()
      expect(store.user).toBeNull()
    })
  })

  describe('isAuthenticated getter', () => {
    it('returns false when user is null', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('returns true when user is set', () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      expect(store.isAuthenticated).toBe(true)
    })
  })

  describe('login action', () => {
    it('posts credentials, fetches /me, populates user', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({ status: 204, data: '' })
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 1, username: 'testuser', email: 'test@example.com' },
      })

      await store.login('testuser', 'password123')

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/auth/login',
        expect.any(FormData),
        expect.any(Object),
      )
      expect(mockedAxios.get).toHaveBeenCalledWith('/api/users/me')
      expect(store.user).toEqual({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
      })
    })

    it('caches user in sessionStorage after login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({ status: 204, data: '' })
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 9, username: 'u', email: 'e@e.com' },
      })

      await store.login('u', 'p')

      const cached = JSON.parse(sessionStorage.getItem('auth.user') || 'null')
      expect(cached).toEqual({ id: 9, username: 'u', email: 'e@e.com' })
    })

    it('throws on failed login', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockRejectedValueOnce(new Error('Unauthorized'))
      await expect(store.login('u', 'wrong')).rejects.toThrow()
      expect(store.user).toBeNull()
    })
  })

  describe('logout action', () => {
    it('calls /logout and clears state', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      sessionStorage.setItem('auth.user', JSON.stringify(store.user))
      mockedAxios.post.mockResolvedValueOnce({ status: 204, data: '' })

      await store.logout()

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/logout')
      expect(store.user).toBeNull()
      expect(sessionStorage.getItem('auth.user')).toBeNull()
    })

    it('clears state even if /logout fails', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      sessionStorage.setItem('auth.user', JSON.stringify(store.user))
      mockedAxios.post.mockRejectedValueOnce(new Error('network'))

      await store.logout()

      expect(store.user).toBeNull()
      expect(sessionStorage.getItem('auth.user')).toBeNull()
    })
  })

  describe('logoutAllDevices action', () => {
    it('calls /logout-all and clears state', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      mockedAxios.post.mockResolvedValueOnce({ status: 204, data: '' })

      await store.logoutAllDevices()

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/logout-all')
      expect(store.user).toBeNull()
    })
  })

  describe('fetchUser action', () => {
    it('sets user after successful request', async () => {
      const store = useAuthStore()
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 5, username: 'fetched', email: 'f@e.com' },
      })

      await store.fetchUser()

      expect(store.user).toEqual({ id: 5, username: 'fetched', email: 'f@e.com' })
    })

    it('returns user object on success', async () => {
      const store = useAuthStore()
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
  })

  describe('refreshAccessToken action', () => {
    it('returns true on successful refresh', async () => {
      const store = useAuthStore()
      mockedAxios.post.mockResolvedValueOnce({ status: 204, data: '' })

      const ok = await store.refreshAccessToken()
      expect(ok).toBe(true)
      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/refresh')
    })

    it('returns false and clears state on failed refresh', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      mockedAxios.post.mockRejectedValueOnce({ response: { status: 401 } })

      const ok = await store.refreshAccessToken()
      expect(ok).toBe(false)
      expect(store.user).toBeNull()
    })
  })

  describe('bootstrap action', () => {
    it('hits /me and sets user on 200', async () => {
      const store = useAuthStore()
      mockedAxios.get.mockResolvedValueOnce({
        data: { id: 1, username: 'u', email: 'e@e.com' },
      })

      await store.bootstrap()

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/users/me')
      expect(store.user).toEqual({ id: 1, username: 'u', email: 'e@e.com' })
      expect(store.bootstrapping).toBe(false)
    })

    it('clears user on 401', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      mockedAxios.get.mockRejectedValueOnce({ response: { status: 401 } })

      await store.bootstrap()

      expect(store.user).toBeNull()
    })

    it('keeps optimistic user on network error', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'u', email: 'e@e.com' }
      mockedAxios.get.mockRejectedValueOnce(new Error('network'))

      await store.bootstrap()

      expect(store.user).toEqual({ id: 1, username: 'u', email: 'e@e.com' })
      expect(store.bootstrapError).toBeTruthy()
    })

    it('is idempotent — repeated calls reuse the same promise', async () => {
      const store = useAuthStore()
      mockedAxios.get.mockResolvedValue({
        data: { id: 1, username: 'u', email: 'e@e.com' },
      })

      const a = store.bootstrap()
      const b = store.bootstrap()
      await Promise.all([a, b])

      expect(mockedAxios.get).toHaveBeenCalledTimes(1)
    })
  })
})

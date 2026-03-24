/**
 * Unit/Integration tests for src/views/LoginView.vue
 *
 * Tests for the login form:
 * - element rendering
 * - form interaction
 * - loading state
 * - error display
 * - navigation after successful login
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory, type Router } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/store/auth'

// Simple test router
const createTestRouter = (): Router =>
  createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      {
        path: '/dashboard',
        name: 'dashboard',
        component: { template: '<div>Dashboard</div>' },
      },
      {
        path: '/register',
        name: 'register',
        component: { template: '<div>Register</div>' },
      },
    ],
  })

describe('LoginView', () => {
  let router: Router

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    router = createTestRouter()
    vi.clearAllMocks()
  })

  const mountLoginView = () =>
    mount(LoginView, {
      global: {
        plugins: [createPinia(), router],
      },
    })

  describe('rendering', () => {
    it('displays the username input field', () => {
      const wrapper = mountLoginView()
      expect(wrapper.find('#username').exists()).toBe(true)
    })

    it('displays the password input field', () => {
      const wrapper = mountLoginView()
      expect(wrapper.find('#password').exists()).toBe(true)
    })

    it('displays the "Sign in" button', () => {
      const wrapper = mountLoginView()
      const button = wrapper.find('button[type="submit"]')
      expect(button.exists()).toBe(true)
      expect(button.text()).toContain('Sign in')
    })

    it('does NOT display an error message initially', () => {
      const wrapper = mountLoginView()
      // Error element is only shown when error is non-empty
      expect(wrapper.find('.text-red-500').exists()).toBe(false)
    })

    it('contains a link to the registration page', () => {
      const wrapper = mountLoginView()
      const registerLink = wrapper.find('a[href="/register"], [to="/register"]')
      expect(registerLink.exists()).toBe(true)
    })
  })

  describe('form interaction', () => {
    it('calls authStore.login with entered credentials on submit', async () => {
      const wrapper = mountLoginView()
      const store = useAuthStore()
      const loginSpy = vi.spyOn(store, 'login').mockResolvedValue(true)

      await wrapper.find('#username').setValue('testuser')
      await wrapper.find('#password').setValue('password123')
      await wrapper.find('form').trigger('submit.prevent')
      await flushPromises()

      expect(loginSpy).toHaveBeenCalledWith('testuser', 'password123')
    })

    it('clears the error field before a new login attempt', async () => {
      const wrapper = mountLoginView()
      const store = useAuthStore()

      // First failed attempt
      vi.spyOn(store, 'login').mockRejectedValueOnce(
        new Error('Wrong credentials'),
      )
      await wrapper.find('form').trigger('submit.prevent')
      await flushPromises()

      // Verify that the error is displayed
      expect(wrapper.find('.text-red-500').exists()).toBe(true)

      // Second attempt — successful
      vi.spyOn(store, 'login').mockResolvedValueOnce(true)
      await wrapper.find('#username').setValue('user')
      await wrapper.find('#password').setValue('pass')
      await wrapper.find('form').trigger('submit.prevent')
      await flushPromises()

      // Error should be cleared
      expect(wrapper.find('.text-red-500').exists()).toBe(false)
    })
  })

  describe('loading state', () => {
    it('disables the button during loading', async () => {
      const wrapper = mountLoginView()
      const store = useAuthStore()

      // Return a Promise that never resolves (simulating an in-flight request)
      vi.spyOn(store, 'login').mockReturnValue(new Promise(() => {}))

      await wrapper.find('#username').setValue('user')
      await wrapper.find('#password').setValue('pass')
      await wrapper.find('form').trigger('submit.prevent')

      // Button should be disabled
      const button = wrapper.find('button[type="submit"]')
      expect(button.attributes('disabled')).toBeDefined()
    })
  })

  describe('error display', () => {
    it('displays error message from API response.data.detail', async () => {
      const wrapper = mountLoginView()
      const store = useAuthStore()
      const axiosError = Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'Incorrect username or password' } },
      })
      vi.spyOn(store, 'login').mockRejectedValue(axiosError)

      await wrapper.find('#username').setValue('wronguser')
      await wrapper.find('#password').setValue('wrongpass')
      await wrapper.find('form').trigger('submit.prevent')
      await flushPromises()

      const errorEl = wrapper.find('.text-red-500')
      expect(errorEl.exists()).toBe(true)
      expect(errorEl.text()).toContain('Incorrect username or password')
    })

    it('displays a generic error when response.data.detail is absent', async () => {
      const wrapper = mountLoginView()
      const store = useAuthStore()
      vi.spyOn(store, 'login').mockRejectedValue(new Error('Network error'))

      await wrapper.find('form').trigger('submit.prevent')
      await flushPromises()

      const errorEl = wrapper.find('.text-red-500')
      expect(errorEl.exists()).toBe(true)
      expect(errorEl.text()).toContain('Login failed')
    })
  })
})

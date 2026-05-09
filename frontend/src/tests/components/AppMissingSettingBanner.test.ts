/**
 * Tests for the missing-household-setting banner rendered by App.vue.
 *
 * The banner is reactive to `householdStore.missingSettingKey`. We mount App
 * with stubs for child components and a real Pinia.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { h } from 'vue'

vi.mock('axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
    defaults: { withCredentials: false, headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}))

const SidebarStub = {
  name: 'AppSidebar',
  render: () => h('aside'),
}
const ModalStub = {
  name: 'EditHouseholdModal',
  props: { household: { type: Object, default: null } },
  emits: ['close'],
  render: () => h('div', { 'data-testid': 'modal' }),
}

describe('App.vue missing-setting banner', () => {
  let App: typeof import('@/App.vue').default

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Lazy-import after Pinia is active so store hydration works.
    App = (await import('@/App.vue')).default
  })

  async function mountApp() {
    const { useAuthStore } = await import('@/store/auth')
    const { useHouseholdStore } = await import('@/store/household')
    const auth = useAuthStore()
    const household = useHouseholdStore()
    auth.user = { id: 1, username: 'u', email: 'u@e.com' }

    const wrapper = mount(App, {
      global: {
        stubs: {
          AppSidebar: SidebarStub,
          EditHouseholdModal: ModalStub,
          'router-view': true,
        },
      },
    })
    await flushPromises()
    return { wrapper, auth, household }
  }

  it('does not render banner when missingSettingKey is null', async () => {
    const { wrapper } = await mountApp()
    expect(wrapper.text()).not.toContain('Missing household setting')
  })

  it('renders banner with the key when missingSettingKey is set', async () => {
    const { wrapper, household } = await mountApp()
    household.missingSettingKey = 'gram_unit_id'
    await flushPromises()

    expect(wrapper.text()).toContain('Missing household setting')
    expect(wrapper.text()).toContain('gram_unit_id')
  })

  it('Dismiss button clears missingSettingKey', async () => {
    const { wrapper, household } = await mountApp()
    household.missingSettingKey = 'ml_unit_id'
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const dismiss = buttons.find((b) => b.text() === 'Dismiss')
    expect(dismiss).toBeTruthy()
    await dismiss!.trigger('click')

    expect(household.missingSettingKey).toBeNull()
  })

  it('shows Configure now button only when a household is selected', async () => {
    const { wrapper, household } = await mountApp()
    household.missingSettingKey = 'gram_unit_id'
    household.households = []
    household.selectedId = null
    await flushPromises()

    const configureBefore = wrapper.findAll('button').find((b) => b.text() === 'Configure now')
    expect(configureBefore).toBeUndefined()

    household.households = [
      {
        id: 1,
        name: 'H',
        role_name: 'admin',
        grocy_url: null,
        address: null,
      } as never,
    ]
    household.selectedId = 1
    await flushPromises()

    const configureAfter = wrapper.findAll('button').find((b) => b.text() === 'Configure now')
    expect(configureAfter).toBeDefined()
  })

  it('Configure now opens the EditHouseholdModal', async () => {
    const { wrapper, household } = await mountApp()
    household.households = [
      {
        id: 1,
        name: 'H',
        role_name: 'admin',
        grocy_url: null,
        address: null,
      } as never,
    ]
    household.selectedId = 1
    household.missingSettingKey = 'portion_unit_id'
    await flushPromises()

    const configure = wrapper.findAll('button').find((b) => b.text() === 'Configure now')
    expect(configure).toBeDefined()
    await configure!.trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="modal"]').exists()).toBe(true)
  })
})

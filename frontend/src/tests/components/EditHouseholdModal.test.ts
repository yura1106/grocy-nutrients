/**
 * Tests for EditHouseholdModal — focuses on the new admin-gated Grocy
 * unit-IDs section: registry-driven dropdowns, current-value-missing
 * warning, save flow (mapping PUT before household PATCH), URL-changed warning.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import EditHouseholdModal from '@/components/household/EditHouseholdModal.vue'
import { useHouseholdStore } from '@/store/household'

async function settle() {
  // The component's watch fires async, kicks off two promises, then re-renders.
  // Two flushPromises + a nextTick covers all microtask + render queues.
  await flushPromises()
  await flushPromises()
  await nextTick()
}

vi.mock('axios', () => {
  const mockAxios = {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    isAxiosError: (err: unknown): boolean =>
      !!err && typeof err === 'object' && 'response' in (err as Record<string, unknown>),
    defaults: { withCredentials: false, headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }
  return { default: mockAxios, isAxiosError: mockAxios.isAxiosError }
})

const ADMIN_HOUSEHOLD = {
  id: 7,
  name: 'Home',
  grocy_url: 'http://grocy.local',
  address: null,
  role_name: 'admin',
} as const

const USER_HOUSEHOLD = {
  ...ADMIN_HOUSEHOLD,
  role_name: 'user',
} as const

const REGISTRY = [
  { key: 'gram_unit_id', type: 'int' },
  { key: 'ml_unit_id', type: 'int' },
  { key: 'portion_unit_id', type: 'int' },
]

const QUANTITY_UNITS = [
  { id: 82, name: 'g' },
  { id: 85, name: 'ml' },
  { id: 9, name: 'Portion' },
]

function setupStore(overrides?: { mapping?: Array<{ key: string; value: string | null }> }) {
  const store = useHouseholdStore()
  store.grocyMappingRegistry = REGISTRY
  store.getGrocyMapping = vi.fn().mockResolvedValue(
    overrides?.mapping ?? [
      { key: 'gram_unit_id', value: '82' },
      { key: 'ml_unit_id', value: '85' },
      { key: 'portion_unit_id', value: '9' },
    ],
  )
  store.getGrocyQuantityUnits = vi.fn().mockResolvedValue(QUANTITY_UNITS)
  store.updateGrocyMapping = vi.fn().mockResolvedValue([])
  store.updateHousehold = vi.fn().mockResolvedValue(undefined)
  store.fetchGrocyMappingRegistry = vi.fn().mockResolvedValue(REGISTRY)
  return store
}

describe('EditHouseholdModal — Grocy unit IDs section', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('does not show mapping section for non-admin members', async () => {
    setupStore()
    const wrapper = mount(EditHouseholdModal, { props: { household: USER_HOUSEHOLD } })
    await settle()

    expect(wrapper.text()).not.toContain('Grocy unit IDs')
  })

  it('renders one dropdown per registry entry for admins', async () => {
    setupStore()
    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    expect(wrapper.text()).toContain('Grocy unit IDs')
    expect(wrapper.text()).toContain('Gram unit')
    expect(wrapper.text()).toContain('Millilitre unit')
    expect(wrapper.text()).toContain('Portion unit')
    expect(wrapper.findAll('select')).toHaveLength(3)
  })

  it('preselects current values from getGrocyMapping', async () => {
    setupStore()
    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    const selects = wrapper.findAll('select')
    expect((selects[0].element as HTMLSelectElement).value).toBe('82')
    expect((selects[1].element as HTMLSelectElement).value).toBe('85')
    expect((selects[2].element as HTMLSelectElement).value).toBe('9')
  })

  it('warns when current value is not in current Grocy units', async () => {
    setupStore({
      mapping: [
        { key: 'gram_unit_id', value: '999' }, // not in QUANTITY_UNITS
        { key: 'ml_unit_id', value: '85' },
        { key: 'portion_unit_id', value: '9' },
      ],
    })
    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    expect(wrapper.text()).toContain('not in current Grocy units')
  })

  it('does not show URL-changed warning when URL is unchanged', async () => {
    setupStore()
    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()
    expect(wrapper.text()).not.toContain('Ви змінили Grocy URL')
  })

  it('shows URL-changed warning when admin edits Grocy URL', async () => {
    setupStore()
    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    const urlInput = wrapper.findAll('input').find((i) => i.attributes('type') === 'url')
    await urlInput!.setValue('http://other.local')
    await settle()

    expect(wrapper.text()).toContain('Ви змінили Grocy URL')
  })

  it('Save calls updateGrocyMapping BEFORE updateHousehold', async () => {
    const store = setupStore()
    const callOrder: string[] = []
    ;(store.updateGrocyMapping as ReturnType<typeof vi.fn>).mockImplementation(async () => {
      callOrder.push('mapping')
      return []
    })
    ;(store.updateHousehold as ReturnType<typeof vi.fn>).mockImplementation(async () => {
      callOrder.push('household')
    })

    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    await wrapper.find('form').trigger('submit')
    await settle()

    expect(callOrder).toEqual(['mapping', 'household'])
  })

  it('does not call updateHousehold when mapping save fails', async () => {
    const store = setupStore()
    ;(store.updateGrocyMapping as ReturnType<typeof vi.fn>).mockRejectedValueOnce({
      response: { status: 422, data: { detail: 'bad' } },
    })

    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    await wrapper.find('form').trigger('submit')
    await settle()

    expect(store.updateHousehold).not.toHaveBeenCalled()
  })

  it('non-admin save path skips mapping update entirely', async () => {
    const store = setupStore()
    const wrapper = mount(EditHouseholdModal, { props: { household: USER_HOUSEHOLD } })
    await settle()

    await wrapper.find('form').trigger('submit')
    await settle()

    expect(store.updateGrocyMapping).not.toHaveBeenCalled()
    expect(store.updateHousehold).toHaveBeenCalled()
  })

  it('Save button is disabled while mapping is loading', async () => {
    const store = setupStore()
    let resolveMapping: (v: Array<{ key: string; value: string | null }>) => void = () => {}
    ;(store.getGrocyMapping as ReturnType<typeof vi.fn>).mockReturnValueOnce(
      new Promise((r) => {
        resolveMapping = r
      }),
    )

    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await flushPromises()

    const saveBtn = wrapper.findAll('button').find((b) => b.text() === 'Save')
    // Vue renders boolean disabled as "" (present) or undefined (absent).
    expect(saveBtn!.attributes('disabled')).toBeDefined()

    resolveMapping([
      { key: 'gram_unit_id', value: '82' },
      { key: 'ml_unit_id', value: '85' },
      { key: 'portion_unit_id', value: '9' },
    ])
    await settle()

    expect(saveBtn!.attributes('disabled')).toBeUndefined()
  })

  it('saving sends value=null for empty selections', async () => {
    setupStore({
      mapping: [
        { key: 'gram_unit_id', value: null },
        { key: 'ml_unit_id', value: '85' },
        { key: 'portion_unit_id', value: '9' },
      ],
    })
    const store = useHouseholdStore()

    const wrapper = mount(EditHouseholdModal, { props: { household: ADMIN_HOUSEHOLD } })
    await settle()

    await wrapper.find('form').trigger('submit')
    await settle()

    const callArgs = (store.updateGrocyMapping as ReturnType<typeof vi.fn>).mock.calls[0]
    const sentItems = callArgs[1] as Array<{ key: string; value: string | null }>
    const gram = sentItems.find((i) => i.key === 'gram_unit_id')
    expect(gram?.value).toBeNull()
  })
})

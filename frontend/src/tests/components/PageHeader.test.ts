/**
 * Unit tests for src/components/PageHeader.vue
 *
 * Covers the navigation/title contract that 12 of 14 pages depend on:
 * - title resolution: prop > route.meta.title
 * - skeleton state when title === null (loading)
 * - icon rendered from route.meta.icon (no override prop)
 * - subtitle rendering
 * - optional slots: above-title, actions, meta
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, defineComponent } from 'vue'
import PageHeader from '@/components/PageHeader.vue'

const mockRoute = { meta: {} as Record<string, unknown> }

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}))

const setMeta = (meta: Record<string, unknown>) => {
  mockRoute.meta = meta
}

const IconStub = defineComponent({
  name: 'IconStub',
  setup() {
    return () => h('svg', { 'data-testid': 'meta-icon' })
  },
})

describe('PageHeader', () => {
  it('renders title from prop when provided', () => {
    setMeta({ title: 'From Meta' })
    const wrapper = mount(PageHeader, { props: { title: 'From Prop' } })
    const h1 = wrapper.find('h1')
    expect(h1.text()).toBe('From Prop')
    expect(h1.classes()).not.toContain('animate-pulse')
  })

  it('falls back to route.meta.title when prop is undefined', () => {
    setMeta({ title: 'Dashboard' })
    const wrapper = mount(PageHeader)
    expect(wrapper.find('h1').text()).toBe('Dashboard')
  })

  it('renders skeleton (animate-pulse, no text) when title is null', () => {
    setMeta({ title: 'Should Not Show' })
    const wrapper = mount(PageHeader, { props: { title: null } })
    const h1 = wrapper.find('h1')
    expect(h1.classes()).toContain('animate-pulse')
    expect(h1.classes()).toContain('bg-gray-200')
    expect(h1.attributes('aria-busy')).toBe('true')
    expect(h1.text().trim()).toBe('')
  })

  it('renders icon when route.meta.icon is set', () => {
    setMeta({ title: 'X', icon: IconStub })
    const wrapper = mount(PageHeader)
    expect(wrapper.find('[data-testid="meta-icon"]').exists()).toBe(true)
  })

  it('renders no icon when route.meta.icon is undefined', () => {
    setMeta({ title: 'X' })
    const wrapper = mount(PageHeader)
    expect(wrapper.find('[data-testid="meta-icon"]').exists()).toBe(false)
  })

  it('renders subtitle paragraph when prop provided', () => {
    setMeta({ title: 'X' })
    const wrapper = mount(PageHeader, { props: { subtitle: 'Helpful subtitle' } })
    expect(wrapper.text()).toContain('Helpful subtitle')
  })

  it('does not render actions wrapper when slot is empty', () => {
    setMeta({ title: 'X' })
    const wrapper = mount(PageHeader)
    expect(wrapper.find('[data-testid="actions-slot"]').exists()).toBe(false)
    const actionsContent = wrapper.findAll('div').some((d) => d.classes().includes('md:ml-4'))
    expect(actionsContent).toBe(false)
  })

  it('renders actions slot content when provided', () => {
    setMeta({ title: 'X' })
    const wrapper = mount(PageHeader, {
      slots: { actions: '<button data-testid="action-btn">Sync</button>' },
    })
    expect(wrapper.find('[data-testid="action-btn"]').exists()).toBe(true)
  })

  it('renders #above-title slot inside the max-w-7xl wrapper', () => {
    setMeta({ title: 'X' })
    const wrapper = mount(PageHeader, {
      slots: { 'above-title': '<a data-testid="back-link">Back</a>' },
    })
    const link = wrapper.find('[data-testid="back-link"]')
    expect(link.exists()).toBe(true)
    expect(link.element.closest('.max-w-7xl')).not.toBeNull()
  })

  it('renders #meta slot below the title row', () => {
    setMeta({ title: 'X' })
    const wrapper = mount(PageHeader, {
      slots: { meta: '<div data-testid="meta-slot">Grocy ID: 1</div>' },
    })
    expect(wrapper.find('[data-testid="meta-slot"]').exists()).toBe(true)
  })
})

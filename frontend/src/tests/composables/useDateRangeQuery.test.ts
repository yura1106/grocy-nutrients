import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useDateRangeQuery } from '@/composables/useDateRangeQuery'

vi.mock('axios', () => ({
  default: {
    get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}))

async function buildHarness(initialQuery: Record<string, string> = {}) {
  let composable!: ReturnType<typeof useDateRangeQuery>
  const Probe = defineComponent({
    setup() {
      composable = useDateRangeQuery()
      return () => h('div')
    },
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: Probe }],
  })
  const initialPath = '/' + (Object.keys(initialQuery).length
    ? '?' + new URLSearchParams(initialQuery).toString()
    : '')
  // Wait for the navigation to commit BEFORE mounting — otherwise the probe
  // sees route.query before the initial URL is applied, and `isDefault` is
  // erroneously `true`. Same applies to setRange tests (router.replace inside
  // setRange would race with an in-flight initial push).
  await router.push(initialPath)
  await router.isReady()
  const wrapper = mount(Probe, { global: { plugins: [router] } })
  return { wrapper, router, get: () => composable }
}

function isoDaysAgo(n: number): string {
  // Match the composable's local-time logic — toISOString() would return UTC.
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - n)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

describe('useDateRangeQuery', () => {
  beforeEach(async () => {
    await nextTick()
  })

  it('defaults to last 7 days when query empty', async () => {
    const { get, router } = await buildHarness({})
    await router.isReady()
    const { from, to, isDefault } = get()
    expect(isDefault.value).toBe(true)
    expect(from.value).toBe(isoDaysAgo(6))
    expect(to.value).toBe(isoDaysAgo(0))
  })

  it('falls back to default when from is invalid', async () => {
    const { get, router } = await buildHarness({ from: 'not-a-date', to: '2026-04-30' })
    await router.isReady()
    const { from, to, isDefault } = get()
    expect(isDefault.value).toBe(true)
    expect(from.value).toBe(isoDaysAgo(6))
    expect(to.value).toBe(isoDaysAgo(0))
  })

  it('falls back when from > to', async () => {
    const { get, router } = await buildHarness({ from: '2026-05-01', to: '2026-04-01' })
    await router.isReady()
    const { isDefault } = get()
    expect(isDefault.value).toBe(true)
  })

  it('returns valid range from query', async () => {
    const { get, router } = await buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    const { from, to, isDefault } = get()
    expect(isDefault.value).toBe(false)
    expect(from.value).toBe('2026-04-01')
    expect(to.value).toBe('2026-04-30')
  })

  it('falls back to default when range exceeds 365 days', async () => {
    const { get, router } = await buildHarness({ from: '2024-01-01', to: '2026-01-01' })
    await router.isReady()
    expect(get().isDefault.value).toBe(true)
  })

  it('setRange writes valid dates to query', async () => {
    const { get, router } = await buildHarness({})
    await router.isReady()
    get().setRange('2026-04-01', '2026-04-30')
    // router.replace inside setRange is async and returns a promise we don't
    // await (fire-and-forget). Flush microtasks so the navigation commits
    // before we read currentRoute.
    await flushPromises()
    expect(router.currentRoute.value.query.from).toBe('2026-04-01')
    expect(router.currentRoute.value.query.to).toBe('2026-04-30')
    expect(get().isDefault.value).toBe(false)
  })

  it('setRange ignores invalid dates', async () => {
    const { get, router } = await buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    get().setRange('garbage', '2026-04-30')
    await nextTick()
    expect(router.currentRoute.value.query.from).toBe('2026-04-01')
  })

  it('setRange ignores ranges over 365 days', async () => {
    const { get, router } = await buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    get().setRange('2024-01-01', '2026-01-01')
    await nextTick()
    expect(router.currentRoute.value.query.from).toBe('2026-04-01')
  })

  it('clearRange removes from/to from query', async () => {
    const { get, router } = await buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    get().clearRange()
    await flushPromises()
    expect(router.currentRoute.value.query.from).toBeUndefined()
    expect(router.currentRoute.value.query.to).toBeUndefined()
    expect(get().isDefault.value).toBe(true)
  })
})

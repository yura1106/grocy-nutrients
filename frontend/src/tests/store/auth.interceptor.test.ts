/**
 * Tests for the 422 missing_household_setting branch of the auth response
 * interceptor (installed by installInterceptors).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import axios from 'axios'
import { useAuthStore } from '@/store/auth'
import { useHouseholdStore } from '@/store/household'

vi.mock('axios', () => {
  const mockAxios = {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} as Record<string, string> } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }
  return { default: mockAxios }
})

const mockedAxios = vi.mocked(axios, true)

function captureResponseRejector(): (error: unknown) => Promise<unknown> {
  // installInterceptors registered the response hook on the axios mock;
  // grab the rejection handler (second arg) from the most recent call.
  const calls = (mockedAxios.interceptors.response.use as unknown as { mock: { calls: unknown[][] } }).mock.calls
  expect(calls.length).toBeGreaterThan(0)
  const last = calls[calls.length - 1]
  return last[1] as (error: unknown) => Promise<unknown>
}

describe('auth interceptor — 422 missing_household_setting', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('sets missingSettingKey on the household store on a matching 422', async () => {
    const auth = useAuthStore()
    const household = useHouseholdStore()
    auth.installInterceptors()

    const rejector = captureResponseRejector()

    const error = {
      config: { url: '/api/some/endpoint' },
      response: {
        status: 422,
        data: { code: 'missing_household_setting', key: 'gram_unit_id' },
      },
    }

    await expect(rejector(error)).rejects.toBe(error)
    expect(household.missingSettingKey).toBe('gram_unit_id')
  })

  it('ignores 422s with a different code', async () => {
    const auth = useAuthStore()
    const household = useHouseholdStore()
    auth.installInterceptors()
    const rejector = captureResponseRejector()

    const error = {
      config: { url: '/api/x' },
      response: { status: 422, data: { code: 'something_else', detail: '...' } },
    }

    await expect(rejector(error)).rejects.toBe(error)
    expect(household.missingSettingKey).toBeNull()
  })

  it('ignores 422s without a key', async () => {
    const auth = useAuthStore()
    const household = useHouseholdStore()
    auth.installInterceptors()
    const rejector = captureResponseRejector()

    const error = {
      config: { url: '/api/x' },
      response: {
        status: 422,
        data: { code: 'missing_household_setting' /* key absent */ },
      },
    }

    await expect(rejector(error)).rejects.toBe(error)
    expect(household.missingSettingKey).toBeNull()
  })

  it('does not interfere with non-422 errors (e.g. 500)', async () => {
    const auth = useAuthStore()
    const household = useHouseholdStore()
    auth.installInterceptors()
    const rejector = captureResponseRejector()

    const error = {
      config: { url: '/api/x' },
      response: { status: 500, data: { detail: 'boom' } },
    }

    await expect(rejector(error)).rejects.toBe(error)
    expect(household.missingSettingKey).toBeNull()
  })

  it('still kicks off refresh on 401 (regression check)', async () => {
    const auth = useAuthStore()
    auth.installInterceptors()
    const rejector = captureResponseRejector()

    // Refresh succeeds → original request retried.
    mockedAxios.post.mockResolvedValueOnce({ status: 204 })
    // Make `axios(originalRequest)` resolvable: the interceptor returns axios(...).
    // The default export is a mock; calling it as a function returns undefined,
    // which is fine for this assertion (we only verify the refresh call).
    const error = {
      config: { url: '/api/users/me' },
      response: { status: 401 },
    }

    // The promise may resolve (via retry) or reject — both are fine. We only
    // care that /api/auth/refresh was invoked.
    try {
      await rejector(error)
    } catch {
      // ignore
    }
    expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/refresh')
  })
})

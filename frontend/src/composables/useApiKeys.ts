import { reactive, toRefs } from 'vue'
import axios, { isAxiosError } from 'axios'

/** Create MCP API keys bound to a household, with one-time plaintext reveal. */
export function useApiKeys() {
  const state = reactive({
    // Household whose create-form is open (null = closed).
    openHouseholdId: null as number | null,
    name: '',
    creating: false,
    createdKey: '', // plaintext, shown once
    copied: false,
    error: '',
  })

  const open = (householdId: number) => {
    state.openHouseholdId = householdId
    state.name = ''
    state.createdKey = ''
    state.copied = false
    state.error = ''
  }

  const close = () => {
    state.openHouseholdId = null
    state.createdKey = ''
  }

  const create = async (householdId: number) => {
    if (!state.name) return
    state.creating = true
    state.error = ''
    try {
      const res = await axios.post<{ key: string }>('/api/users/me/api-keys', {
        name: state.name,
        household_id: householdId,
      })
      state.createdKey = res.data.key
    } catch (err: unknown) {
      state.error =
        (isAxiosError(err) && err.response?.data?.detail) || 'Failed to create API key'
    } finally {
      state.creating = false
    }
  }

  const copyKey = async () => {
    await navigator.clipboard.writeText(state.createdKey)
    state.copied = true
  }

  return {
    ...toRefs(state),
    open,
    close,
    create,
    copyKey,
  }
}

import { reactive, toRefs } from 'vue'
import { isAxiosError } from 'axios'
import { useHouseholdStore } from '../store/household'

export function useGrocyKey() {
  const householdStore = useHouseholdStore()

  const state = reactive({
    target: null as { householdId: number; userId: number } | null,
    value: '',
    saving: false,
    error: '',
  })

  const open = async (householdId: number, userId: number) => {
    state.target = { householdId, userId }
    state.value = ''
    state.error = ''
    const key = await householdStore.getGrocyKey(householdId)
    if (key) state.value = key
  }

  const save = async (householdId: number) => {
    state.saving = true
    state.error = ''
    try {
      await householdStore.saveGrocyKey(householdId, state.value)
      state.target = null
    } catch (err: unknown) {
      state.error = isAxiosError(err) && err.response?.data?.detail || 'Failed to save API key'
    } finally {
      state.saving = false
    }
  }

  const close = () => {
    state.target = null
  }

  return {
    ...toRefs(state),
    open,
    save,
    close,
  }
}

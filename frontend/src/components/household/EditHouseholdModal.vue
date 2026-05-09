<template>
  <div
    v-if="household"
    class="fixed inset-0 z-50 overflow-y-auto"
  >
    <div class="flex items-center justify-center min-h-screen px-4">
      <div
        class="fixed inset-0 bg-gray-500/75"
        @click="emit('close')"
      ></div>
      <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Edit Household</h3>
        <form
          @submit.prevent="handleSubmit"
          class="space-y-4"
        >
          <div>
            <label class="block text-sm font-medium text-gray-700">Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="mt-1 shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Grocy URL</label>
            <input
              v-model="form.grocy_url"
              type="url"
              placeholder="http://192.168.1.1:9192"
              class="mt-1 shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Address</label>
            <input
              v-model="form.address"
              type="text"
              class="mt-1 shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>

          <div
            v-if="isAdmin"
            class="pt-4 border-t border-gray-200"
          >
            <h4 class="text-sm font-semibold text-gray-900 mb-2">Grocy unit IDs</h4>
            <p
              v-if="urlChanged"
              class="text-xs text-amber-600 mb-2"
            >
              Ви змінили Grocy URL — перевірте unit IDs після збереження.
            </p>
            <p
              v-if="mappingError"
              class="text-xs text-red-500 mb-2"
            >
              {{ mappingError }}
            </p>
            <div
              v-for="entry in registry"
              :key="entry.key"
              class="mb-3"
            >
              <label class="block text-sm font-medium text-gray-700">
                {{ keyLabel(entry.key) }}
              </label>
              <select
                v-model="mappingValues[entry.key]"
                :disabled="quantityUnitsLoading"
                class="mt-1 block w-full sm:text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
              >
                <option :value="null">— not set —</option>
                <option
                  v-if="quantityUnitsLoading"
                  disabled
                >
                  Loading units…
                </option>
                <option
                  v-for="unit in quantityUnits"
                  :key="unit.id"
                  :value="String(unit.id)"
                >
                  {{ unit.name }} (#{{ unit.id }})
                </option>
              </select>
              <p
                v-if="!quantityUnitsLoading && currentValueMissingFromUnits(entry.key)"
                class="text-xs text-amber-600 mt-1"
              >
                Current value #{{ mappingValues[entry.key] }} not in current Grocy units.
              </p>
            </div>
          </div>

          <p
            v-if="error"
            class="text-sm text-red-500"
          >
            {{ error }}
          </p>
          <div class="flex justify-end space-x-3">
            <button
              type="button"
              @click="emit('close')"
              class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="saveDisabled"
              class="py-2 px-4 border border-transparent shadow-xs text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {{ loading ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useHouseholdStore } from '../../store/household'
import { parseApiError } from '../../utils/parseApiError'
import type {
  HouseholdWithRole,
  GrocyMappingItem,
  GrocyQuantityUnit,
} from '../../types/household'

const props = defineProps<{ household: HouseholdWithRole | null }>()
const emit = defineEmits<{ close: [] }>()

const householdStore = useHouseholdStore()
const loading = ref(false)
const error = ref('')
const form = reactive({ name: '', grocy_url: '', address: '' })

const initialUrl = ref<string>('')
const isAdmin = computed(() => props.household?.role_name === 'admin')

const registry = computed(() => householdStore.grocyMappingRegistry || [])

const mappingValues = reactive<Record<string, string | null>>({})
const mappingLoading = ref(false)
const mappingError = ref('')
const mappingLoaded = ref(false)

const quantityUnits = ref<GrocyQuantityUnit[]>([])
const quantityUnitsLoading = ref(false)

const KEY_LABELS: Record<string, string> = {
  gram_unit_id: 'Gram unit',
  ml_unit_id: 'Millilitre unit',
  portion_unit_id: 'Portion unit',
}

function keyLabel(key: string): string {
  return KEY_LABELS[key] || key
}

const urlChanged = computed(() => isAdmin.value && form.grocy_url !== initialUrl.value)

const saveDisabled = computed(() => {
  if (loading.value) return true
  if (isAdmin.value && (!mappingLoaded.value || quantityUnitsLoading.value)) return true
  return false
})

function currentValueMissingFromUnits(key: string): boolean {
  const v = mappingValues[key]
  if (v === null || v === undefined || v === '') return false
  if (quantityUnitsLoading.value) return false
  return !quantityUnits.value.some((u) => String(u.id) === v)
}

async function loadMappingAndUnits(householdId: number) {
  if (!isAdmin.value) return
  mappingLoading.value = true
  mappingLoaded.value = false
  quantityUnitsLoading.value = true
  mappingError.value = ''

  // Reset reactive map for current registry keys
  for (const e of registry.value) mappingValues[e.key] = null

  const mappingPromise = householdStore.getGrocyMapping(householdId)
    .then((items: GrocyMappingItem[]) => {
      for (const item of items) {
        mappingValues[item.key] = item.value ?? null
      }
      mappingLoaded.value = true
    })
    .catch((err: unknown) => {
      mappingError.value = parseApiError(err, 'Failed to load Grocy unit IDs')
    })
    .finally(() => {
      mappingLoading.value = false
    })

  const unitsPromise = householdStore.getGrocyQuantityUnits(householdId)
    .then((units) => {
      quantityUnits.value = units
    })
    .catch((err: unknown) => {
      mappingError.value = parseApiError(err, 'Failed to load Grocy quantity units')
    })
    .finally(() => {
      quantityUnitsLoading.value = false
    })

  await Promise.all([mappingPromise, unitsPromise])
}

watch(() => props.household, async (h) => {
  if (h) {
    form.name = h.name
    form.grocy_url = h.grocy_url || ''
    form.address = h.address || ''
    initialUrl.value = h.grocy_url || ''
    error.value = ''
    mappingError.value = ''
    quantityUnits.value = []
    mappingLoaded.value = false

    if (!householdStore.grocyMappingRegistry) {
      await householdStore.fetchGrocyMappingRegistry()
    }
    await loadMappingAndUnits(h.id)
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!props.household) return
  loading.value = true
  error.value = ''
  mappingError.value = ''
  try {
    if (isAdmin.value) {
      const items = registry.value.map((e) => ({
        key: e.key,
        value: mappingValues[e.key] || null,
      }))
      try {
        await householdStore.updateGrocyMapping(props.household.id, items)
      } catch (mapErr: unknown) {
        mappingError.value = parseApiError(mapErr, 'Failed to save Grocy unit IDs')
        loading.value = false
        return
      }
    }

    await householdStore.updateHousehold(props.household.id, {
      name: form.name,
      grocy_url: form.grocy_url || null,
      address: form.address || null,
    })
    emit('close')
  } catch (err: unknown) {
    error.value = parseApiError(err, 'Failed to update household')
  } finally {
    loading.value = false
  }
}
</script>

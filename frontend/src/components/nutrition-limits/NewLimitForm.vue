<!-- frontend/src/components/nutrition-limits/NewLimitForm.vue -->
<template>
  <div class="bg-white shadow-sm sm:rounded-lg p-6">
    <h3 class="text-lg font-medium text-gray-900 mb-4">Set Daily Limits</h3>

    <div class="flex flex-wrap gap-3 mb-4 items-end">
      <div class="w-32">
        <label class="block text-xs font-medium text-gray-700 mb-1">Date</label>
        <input
          ref="dateInputRef"
          type="text"
          readonly
          placeholder="YYYY-MM-DD"
          class="block w-full py-1 px-2 text-sm border-gray-300 rounded-md shadow-xs focus:ring-indigo-500 focus:border-indigo-500 bg-white cursor-pointer"
        />
      </div>
      <div class="w-28">
        <label class="block text-xs font-medium text-gray-700 mb-1">Calories Burned</label>
        <input
          v-model.number="form.calories_burned"
          type="number"
          min="500"
          max="10000"
          step="1"
          placeholder="2000"
          class="block w-full py-1 px-2 text-sm border-gray-300 rounded-md shadow-xs focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>
      <div class="w-24">
        <label class="block text-xs font-medium text-gray-700 mb-1">Weight (kg)</label>
        <input
          v-model.number="form.body_weight"
          type="number"
          min="20"
          max="500"
          step="0.1"
          placeholder="75"
          class="block w-full py-1 px-2 text-sm border-gray-300 rounded-md shadow-xs focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>
      <div class="w-56">
        <label class="block text-xs font-medium text-gray-700 mb-1">Activity Level</label>
        <VueMultiselect
          v-model="selectedActivityLevel"
          :options="activityLevelOptions"
          :searchable="false"
          :close-on-select="true"
          :show-labels="false"
          label="label"
          track-by="value"
          placeholder="Select activity level"
          class="multiselect-sm"
        />
      </div>
    </div>

    <div class="flex gap-3 mb-4">
      <button
        @click="generate"
        :disabled="!canGenerate || store.previewLoading"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
      >
        {{ store.previewLoading ? 'Calculating...' : 'Generate' }}
      </button>
      <button
        @click="fillFromProfile"
        :disabled="!healthStore.params"
        class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
      >
        Fill from Profile
      </button>
    </div>

    <!-- Preview -->
    <div
      v-if="nutrients"
      class="mb-4 bg-indigo-50 rounded-lg p-4"
    >
      <div class="grid grid-cols-4 gap-2 text-sm">
        <div
          v-for="field in previewFields"
          :key="field.key"
          class="text-center"
        >
          <div class="font-semibold text-indigo-800">{{ fmt(nutrients[field.key]) }}</div>
          <div class="text-xs text-gray-500">{{ field.label }}</div>
        </div>
      </div>
    </div>

    <div
      v-if="store.error"
      class="text-red-500 text-sm mb-4"
    >
      {{ store.error }}
    </div>

    <button
      v-if="nutrients"
      @click="save"
      :disabled="store.loading"
      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
    >
      {{ store.loading ? 'Saving...' : 'Save' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import VueMultiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'
import { useNutritionLimitsStore } from '../../store/nutritionLimits'
import { useHealthStore } from '../../store/health'
import type { NutrientLimitsPreview } from '../../types/nutritionLimit'
import type { ActivityLevel } from '../../types/health'
import { ACTIVITY_LEVEL_LABELS } from '../../types/health'

const store = useNutritionLimitsStore()
const healthStore = useHealthStore()

const today = new Date().toISOString().slice(0, 10)

// --- Activity level multiselect ---
interface SelectOption<T> { value: T; label: string }

const activityLevelOptions: SelectOption<ActivityLevel>[] = Object.entries(ACTIVITY_LEVEL_LABELS).map(
  ([value, label]) => ({ value: value as ActivityLevel, label }),
)

const selectedActivityLevel = ref<SelectOption<ActivityLevel> | null>(null)

// --- Flatpickr ---
const dateInputRef = ref<HTMLInputElement | null>(null)

// --- Form state ---
const form = reactive({
  date: today,
  calories_burned: null as number | null,
  body_weight: null as number | null,
  activity_level: '' as string,
})

// Sync multiselect → form
watch(selectedActivityLevel, (opt) => { form.activity_level = opt?.value ?? '' })

function applyProfileDefaults(params: typeof healthStore.params) {
  if (!params) return
  if (form.body_weight === null) form.body_weight = params.weight ?? null
  if (!selectedActivityLevel.value && params.activity_level) {
    selectedActivityLevel.value = activityLevelOptions.find((o) => o.value === params.activity_level) ?? null
  }
}

onMounted(() => {
  if (dateInputRef.value) {
    flatpickr(dateInputRef.value, {
      dateFormat: 'Y-m-d',
      defaultDate: today,
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => { form.date = dateStr || today },
    })
  }

  if (!healthStore.params) {
    healthStore.fetchHealthParams()
  } else {
    applyProfileDefaults(healthStore.params)
  }
})

watch(
  () => healthStore.params,
  (params) => applyProfileDefaults(params),
)

const canGenerate = computed(() =>
  form.calories_burned !== null && form.body_weight !== null && form.activity_level !== '',
)

const nutrients = computed((): NutrientLimitsPreview | null => store.preview)

const previewFields: { key: keyof NutrientLimitsPreview; label: string }[] = [
  { key: 'calories', label: 'kcal' },
  { key: 'proteins', label: 'protein' },
  { key: 'carbohydrates', label: 'carbs' },
  { key: 'fats', label: 'fats' },
  { key: 'fibers', label: 'fiber' },
  { key: 'salt', label: 'salt' },
  { key: 'fats_saturated', label: 'sat.fat' },
  { key: 'carbohydrates_of_sugars', label: 'sugars' },
]

const fmt = (val: number) => val.toFixed(1)

async function generate() {
  if (!canGenerate.value) return
  await store.previewLimits({
    calories_burned: form.calories_burned!,
    body_weight: form.body_weight!,
    activity_level: form.activity_level,
  })
}

function fillFromProfile() {
  const p = healthStore.params
  if (!p) return
  form.body_weight = p.weight ?? null
  selectedActivityLevel.value = p.activity_level
    ? activityLevelOptions.find((o) => o.value === p.activity_level) ?? null
    : null
  store.preview = {
    calories: p.daily_calories ?? 0,
    proteins: p.daily_proteins ?? 0,
    carbohydrates: p.daily_carbohydrates ?? 0,
    carbohydrates_of_sugars: p.daily_carbohydrates_of_sugars ?? 0,
    fats: p.daily_fats ?? 0,
    fats_saturated: p.daily_fats_saturated ?? 0,
    salt: p.daily_salt ?? 0,
    fibers: p.daily_fibers ?? 0,
  }
}

const emit = defineEmits<{ created: [] }>()

async function save() {
  if (!nutrients.value) return
  await store.createLimit({
    date: form.date,
    calories_burned: form.calories_burned,
    body_weight: form.body_weight,
    activity_level: form.activity_level || null,
    ...nutrients.value,
  })
  form.date = today
  form.calories_burned = null
  form.body_weight = healthStore.params?.weight ?? null
  selectedActivityLevel.value = healthStore.params?.activity_level
    ? activityLevelOptions.find((o) => o.value === healthStore.params!.activity_level) ?? null
    : null
  emit('created')
}
</script>

<style>
.multiselect-sm.multiselect {
  min-height: 30px;
  font-size: 0.875rem;
}
.multiselect-sm .multiselect__tags {
  min-height: 30px;
  padding: 4px 36px 0 8px;
  font-size: 0.875rem;
}
.multiselect-sm .multiselect__select {
  height: 30px;
}
.multiselect-sm .multiselect__single,
.multiselect-sm .multiselect__placeholder {
  font-size: 0.875rem;
  line-height: 1.4;
}
</style>

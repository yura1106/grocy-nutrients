<template>
  <div class="bg-white shadow-sm overflow-hidden sm:rounded-lg mt-6">
    <div class="px-4 py-5 sm:px-6">
      <h3 class="text-lg leading-6 font-medium text-gray-900">Health Parameters</h3>
      <p class="mt-1 max-w-2xl text-sm text-gray-500">Set your body measurements and daily nutrient goals</p>
    </div>
    <div class="border-t border-gray-200">
      <form
        @submit.prevent="save"
        class="p-6"
      >
        <!-- Body Measurements -->
        <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label
              for="height"
              class="block text-sm font-medium text-gray-700"
            >Height (cm)</label>
            <div class="mt-1">
              <input
                id="height"
                v-model.number="form.height"
                type="number"
                min="50"
                max="300"
                step="0.1"
                placeholder="170"
                class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
              />
            </div>
          </div>

          <div>
            <label
              for="weight"
              class="block text-sm font-medium text-gray-700"
            >Weight (kg)</label>
            <div class="mt-1">
              <input
                id="weight"
                v-model.number="form.weight"
                type="number"
                min="20"
                max="500"
                step="0.1"
                placeholder="70"
                class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Gender</label>
            <VueMultiselect
              v-model="selectedGender"
              :options="genderOptions"
              :searchable="false"
              :close-on-select="true"
              :show-labels="false"
              label="label"
              track-by="value"
              placeholder="Select gender"
            />
          </div>

          <div>
            <label
              for="date_of_birth"
              class="block text-sm font-medium text-gray-700"
            >Date of Birth</label>
            <div class="mt-1">
              <input
                id="date_of_birth"
                ref="dobInputRef"
                :value="form.date_of_birth || ''"
                type="text"
                readonly
                placeholder="YYYY-MM-DD"
                class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md bg-white cursor-pointer"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Activity Level</label>
            <VueMultiselect
              v-model="selectedActivityLevel"
              :options="activityLevelOptions"
              :searchable="false"
              :close-on-select="true"
              :show-labels="false"
              label="label"
              track-by="value"
              placeholder="Select activity level"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Goal</label>
            <VueMultiselect
              v-model="selectedGoal"
              :options="goalOptions"
              :searchable="false"
              :close-on-select="true"
              :show-labels="false"
              label="label"
              track-by="value"
              placeholder="Select goal"
            />
          </div>

          <div>
            <label
              for="calorie_deficit_percent"
              class="block text-sm font-medium text-gray-700"
            >% Deficit / Surplus from TDEE</label>
            <div class="mt-1">
              <input
                id="calorie_deficit_percent"
                v-model.number="form.calorie_deficit_percent"
                type="number"
                min="0"
                max="50"
                step="1"
                placeholder="15"
                class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
              />
            </div>
            <p class="mt-1 text-xs text-gray-400">Used for auto-calculating daily limits. Default: 15%.</p>
          </div>
        </div>

        <!-- BMI Display -->
        <div
          v-if="bmi !== null"
          class="mt-4 p-4 bg-gray-50 rounded-lg flex items-center gap-3"
        >
          <span class="text-sm font-medium text-gray-700">BMI: {{ bmi.toFixed(1) }}</span>
          <span
            :class="bmiCategory!.color"
            class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
          >
            {{ bmiCategory!.label }}
          </span>
        </div>

        <!-- Auto-calculate button -->
        <div class="mt-6">
          <button
            type="button"
            :disabled="!canAutoCalculate"
            @click="autoCalculate"
            class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-xs text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Calculate daily norms
          </button>
          <p class="mt-1 text-xs text-gray-500">Based on Mifflin-St Jeor equation. Requires all body fields above.</p>
        </div>

        <!-- Daily Nutrient Limits -->
        <h4 class="mt-6 text-md font-medium text-gray-900">Daily Nutrient Limits</h4>
        <div class="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div
            v-for="field in nutrientFields"
            :key="field.key"
          >
            <label
              :for="field.key"
              class="block text-sm font-medium text-gray-700"
            >{{ field.label }}</label>
            <div class="mt-1 relative">
              <input
                :id="field.key"
                :value="form[field.key]"
                @input="onNutrientInput(field.key, $event)"
                type="number"
                :min="field.min"
                :max="field.max"
                :step="field.step"
                class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                :class="{ 'pr-20': savedValue(field.key) !== null && hasChanged(field.key) }"
              />
              <span
                v-if="savedValue(field.key) !== null && hasChanged(field.key)"
                class="absolute inset-y-0 right-0 flex items-center pr-3 text-xs text-gray-400 pointer-events-none"
                :title="'Saved: ' + savedValue(field.key)"
              >
                was {{ savedValue(field.key) }}
              </span>
            </div>
          </div>
        </div>

        <div
          v-if="healthStore.error"
          class="mt-4 text-red-500 text-sm"
        >
          {{ healthStore.error }}
        </div>

        <div
          v-if="healthStore.success"
          class="mt-4 text-green-500 text-sm"
        >
          {{ healthStore.success }}
        </div>

        <div class="mt-6">
          <button
            type="submit"
            :disabled="healthStore.loading"
            class="inline-flex justify-center py-2 px-4 border border-transparent shadow-xs text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <svg
              v-if="healthStore.loading"
              class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Save
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import VueMultiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'
import { useHealthStore } from '../../store/health'
import { useHealthCalculations } from '../../composables/useHealthCalculations'
import type { Gender, ActivityLevel, Goal, HealthParameters } from '../../types/health'
import { GENDER_LABELS, ACTIVITY_LEVEL_LABELS, GOAL_LABELS } from '../../types/health'

const healthStore = useHealthStore()
const { calcBMR, calcTDEE, calcGoalCalories, calcBMI, getBMICategory, calcMacros, ageFromDOB } =
  useHealthCalculations()

// --- Multiselect option lists ---
interface SelectOption<T> { value: T; label: string }

const genderOptions: SelectOption<Gender>[] = Object.entries(GENDER_LABELS).map(
  ([value, label]) => ({ value: value as Gender, label })
)

const activityLevelOptions: SelectOption<ActivityLevel>[] = Object.entries(ACTIVITY_LEVEL_LABELS).map(
  ([value, label]) => ({ value: value as ActivityLevel, label })
)

const goalOptions: SelectOption<Goal>[] = Object.entries(GOAL_LABELS).map(
  ([value, label]) => ({ value: value as Goal, label })
)

// --- Multiselect v-models (object-based for vue-multiselect) ---
const selectedGender = ref<SelectOption<Gender> | null>(null)
const selectedActivityLevel = ref<SelectOption<ActivityLevel> | null>(null)
const selectedGoal = ref<SelectOption<Goal> | null>(null)

// Sync multiselect → form
watch(selectedGender, (opt) => { form.gender = opt?.value ?? null })
watch(selectedActivityLevel, (opt) => { form.activity_level = opt?.value ?? null })
watch(selectedGoal, (opt) => { form.goal = opt?.value ?? null })

// --- Flatpickr ref ---
const dobInputRef = ref<HTMLInputElement | null>(null)

// --- Nutrient field definitions ---
type NutrientKey = keyof Pick<HealthParameters,
  'daily_calories' | 'daily_proteins' | 'daily_fats' | 'daily_fats_saturated' |
  'daily_carbohydrates' | 'daily_carbohydrates_of_sugars' | 'daily_salt' | 'daily_fibers'>

const nutrientFields: { key: NutrientKey; label: string; min: number; max: number; step: number }[] = [
  { key: 'daily_calories', label: 'Calories (kcal)', min: 0, max: 10000, step: 1 },
  { key: 'daily_proteins', label: 'Proteins (g)', min: 0, max: 1000, step: 1 },
  { key: 'daily_fats', label: 'Fats (g)', min: 0, max: 1000, step: 1 },
  { key: 'daily_fats_saturated', label: 'Saturated Fats (g)', min: 0, max: 500, step: 1 },
  { key: 'daily_carbohydrates', label: 'Carbohydrates (g)', min: 0, max: 2000, step: 1 },
  { key: 'daily_carbohydrates_of_sugars', label: 'Sugars (g)', min: 0, max: 1000, step: 1 },
  { key: 'daily_salt', label: 'Salt (g)', min: 0, max: 100, step: 0.1 },
  { key: 'daily_fibers', label: 'Fiber (g)', min: 0, max: 200, step: 1 },
]

// --- Form state ---
const form = reactive({
  height: null as number | null,
  weight: null as number | null,
  gender: null as Gender | null,
  date_of_birth: null as string | null,
  activity_level: null as ActivityLevel | null,
  goal: null as Goal | null,
  daily_calories: null as number | null,
  daily_proteins: null as number | null,
  daily_fats: null as number | null,
  daily_fats_saturated: null as number | null,
  daily_carbohydrates: null as number | null,
  daily_carbohydrates_of_sugars: null as number | null,
  daily_salt: null as number | null,
  daily_fibers: null as number | null,
  calorie_deficit_percent: null as number | null,
})

// --- Saved (DB) snapshot for "was X" comparison ---
const saved = reactive({
  daily_calories: null as number | null,
  daily_proteins: null as number | null,
  daily_fats: null as number | null,
  daily_fats_saturated: null as number | null,
  daily_carbohydrates: null as number | null,
  daily_carbohydrates_of_sugars: null as number | null,
  daily_salt: null as number | null,
  daily_fibers: null as number | null,
})

function savedValue(key: NutrientKey): number | null {
  return saved[key]
}

function hasChanged(key: NutrientKey): boolean {
  return form[key] !== saved[key]
}

function onNutrientInput(key: NutrientKey, event: Event) {
  const val = (event.target as HTMLInputElement).value
  form[key] = val === '' ? null : Number(val)
}

function snapshotSaved() {
  const p = healthStore.params
  for (const f of nutrientFields) {
    saved[f.key] = p?.[f.key] ?? null
  }
}

// --- BMI ---
const bmi = computed(() => {
  if (form.height && form.weight && form.height > 0) {
    return calcBMI(form.weight, form.height)
  }
  return null
})

const bmiCategory = computed(() => {
  if (bmi.value !== null) {
    return getBMICategory(bmi.value)
  }
  return null
})

// --- Auto-calculate ---
const canAutoCalculate = computed(() => {
  return (
    form.height !== null &&
    form.weight !== null &&
    form.gender !== null &&
    form.date_of_birth !== null &&
    form.activity_level !== null &&
    form.goal !== null
  )
})

function autoCalculate() {
  if (!canAutoCalculate.value) return

  const age = ageFromDOB(form.date_of_birth!)
  const bmr = calcBMR(form.weight!, form.height!, age, form.gender!)
  const tdee = calcTDEE(bmr, form.activity_level!)
  const goalCalories = calcGoalCalories(tdee, form.goal!)
  const macros = calcMacros(goalCalories, form.weight!, form.goal!)

  form.daily_calories = macros.daily_calories
  form.daily_proteins = macros.daily_proteins
  form.daily_fats = macros.daily_fats
  form.daily_fats_saturated = macros.daily_fats_saturated
  form.daily_carbohydrates = macros.daily_carbohydrates
  form.daily_carbohydrates_of_sugars = macros.daily_carbohydrates_of_sugars
  form.daily_salt = macros.daily_salt
  form.daily_fibers = macros.daily_fibers
}

// --- Populate form from store ---
function populateForm() {
  const p = healthStore.params
  if (!p) return

  form.height = p.height
  form.weight = p.weight
  form.gender = p.gender
  form.date_of_birth = p.date_of_birth
  form.activity_level = p.activity_level
  form.goal = p.goal
  form.daily_calories = p.daily_calories
  form.daily_proteins = p.daily_proteins
  form.daily_fats = p.daily_fats
  form.daily_fats_saturated = p.daily_fats_saturated
  form.daily_carbohydrates = p.daily_carbohydrates
  form.daily_carbohydrates_of_sugars = p.daily_carbohydrates_of_sugars
  form.daily_salt = p.daily_salt
  form.daily_fibers = p.daily_fibers
  form.calorie_deficit_percent = p.calorie_deficit_percent ?? null

  // Set multiselect objects
  selectedGender.value = p.gender
    ? genderOptions.find((o) => o.value === p.gender) ?? null
    : null
  selectedActivityLevel.value = p.activity_level
    ? activityLevelOptions.find((o) => o.value === p.activity_level) ?? null
    : null
  selectedGoal.value = p.goal
    ? goalOptions.find((o) => o.value === p.goal) ?? null
    : null
}

// --- Save ---
async function save() {
  const payload: Record<string, string | number | null> = {}
  for (const [key, value] of Object.entries(form)) {
    if (value !== null && value !== '') {
      payload[key] = value
    }
  }

  try {
    await healthStore.updateHealthParams(payload)
    snapshotSaved()
  } catch {
    // error is already set in the store
  }
}

// --- Init ---
onMounted(async () => {
  await healthStore.fetchHealthParams()
  populateForm()
  snapshotSaved()

  // Init flatpickr for date of birth
  if (dobInputRef.value) {
    flatpickr(dobInputRef.value, {
      dateFormat: 'Y-m-d',
      defaultDate: form.date_of_birth || undefined,
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => {
        form.date_of_birth = dateStr || null
      },
    })
  }
})
</script>

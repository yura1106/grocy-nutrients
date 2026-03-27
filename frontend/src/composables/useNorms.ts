import { computed, unref } from 'vue'
import type { MaybeRef } from 'vue'
import { useNutritionLimitsStore } from '../store/nutritionLimits'
import { useHealthStore } from '../store/health'
import type { NutritionLimit } from '../types/nutritionLimit'
import type { HealthParameters } from '../types/health'

export interface NormValues {
  daily_calories: number | null
  daily_proteins: number | null
  daily_fats: number | null
  daily_fats_saturated: number | null
  daily_carbohydrates: number | null
  daily_carbohydrates_of_sugars: number | null
  daily_salt: number | null
  daily_fibers: number | null
}

/** Build NormValues from a daily limit record, falling back to health profile params. */
export function normsFromSources(
  limit: NutritionLimit | null | undefined,
  params: HealthParameters | null,
): NormValues | null {
  if (limit) {
    return {
      daily_calories: limit.calories,
      daily_proteins: limit.proteins,
      daily_fats: limit.fats,
      daily_fats_saturated: limit.fats_saturated,
      daily_carbohydrates: limit.carbohydrates,
      daily_carbohydrates_of_sugars: limit.carbohydrates_of_sugars,
      daily_salt: limit.salt,
      daily_fibers: limit.fibers,
    }
  }
  if (params) {
    return {
      daily_calories: params.daily_calories,
      daily_proteins: params.daily_proteins,
      daily_fats: params.daily_fats,
      daily_fats_saturated: params.daily_fats_saturated,
      daily_carbohydrates: params.daily_carbohydrates,
      daily_carbohydrates_of_sugars: params.daily_carbohydrates_of_sugars,
      daily_salt: params.daily_salt,
      daily_fibers: params.daily_fibers,
    }
  }
  return null
}

export function useNorms(date?: MaybeRef<string | null>) {
  const limitsStore = useNutritionLimitsStore()
  const healthStore = useHealthStore()

  const norms = computed((): NormValues | null => {
    const d = date !== undefined ? unref(date) : null
    const limit = d ? limitsStore.getLimitByDate(d) : limitsStore.todayLimit
    return normsFromSources(limit, healthStore.params)
  })

  return { norms }
}

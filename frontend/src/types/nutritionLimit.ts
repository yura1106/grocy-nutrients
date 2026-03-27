export interface NutritionLimit {
  id: number
  date: string
  calories_burned: number | null
  body_weight: number | null
  activity_level: string | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

export interface NutrientLimitsPreview {
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  salt: number
  fibers: number
}

export interface NutritionLimitCreate {
  date: string
  calories_burned?: number | null
  body_weight?: number | null
  activity_level?: string | null
  calories?: number | null
  proteins?: number | null
  carbohydrates?: number | null
  carbohydrates_of_sugars?: number | null
  fats?: number | null
  fats_saturated?: number | null
  salt?: number | null
  fibers?: number | null
}

export interface NutritionLimitUpdate {
  calories_burned?: number | null
  body_weight?: number | null
  activity_level?: string | null
  calories?: number | null
  proteins?: number | null
  carbohydrates?: number | null
  carbohydrates_of_sugars?: number | null
  fats?: number | null
  fats_saturated?: number | null
  salt?: number | null
  fibers?: number | null
}

export interface PreviewRequest {
  calories_burned: number
  body_weight: number
  activity_level: string
}

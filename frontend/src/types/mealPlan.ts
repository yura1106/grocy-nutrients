export type MealPlanLineType = 'product' | 'recipe'
export type MealPlanLineStatus = 'pending' | 'syncing' | 'synced' | 'failed'

export interface MealPlanLine {
  id: number
  household_id: number
  user_id: number | null

  grocy_meal_plan_id: number | null
  grocy_shadow_recipe_id: number | null

  type: MealPlanLineType
  day: string // YYYY-MM-DD
  section_id: number

  product_id: number | null
  product_amount: string | null
  product_amount_stock: string | null
  product_qu_id: number | null
  product_qu_name: string | null

  recipe_id: number | null
  recipe_servings: string | null

  product_name: string | null
  recipe_name: string | null

  product_local_id: number | null
  recipe_local_id: number | null

  status: MealPlanLineStatus
  error_message: string | null
  retry_count: number

  done: boolean
  done_at: string | null

  created_at: string | null
  updated_at: string | null
}

export interface MealPlanLineCreate {
  type: MealPlanLineType
  day: string
  section_id: number

  product_id?: number | null
  product_amount?: string | number | null
  product_amount_stock?: string | number | null
  product_qu_id?: number | null

  recipe_id?: number | null
  recipe_servings?: string | number | null
}

export interface MealPlanLineEdit {
  product_amount?: string | number | null
  product_amount_stock?: string | number | null
  recipe_servings?: string | number | null
}

export interface MealPlanSection {
  section_id: number
  name: string
  sort_number: number | null
}

export interface MealPlanUnit {
  qu_id: number
  name: string
  name_plural: string | null
  is_stock_default: boolean
  factor_to_stock: number
}

export interface MealPlanJobStatus {
  task_id: string
  state: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'NONE'
  current: number
  total: number
  errors: string[]
  summary: { synced: number; failed: number; unmatched: number; errors: string[] } | null
  error: string | null
  // Client-side: days that were submitted in this batch. Used after job
  // completion to decide whether to reload the current range — if the user
  // has navigated to a non-overlapping range, the reload is skipped.
  submitted_days?: string[]
}

export interface MealPlanMissingItem {
  type: 'product' | 'recipe'
  grocy_id: number
  name: string
}

export interface MealPlanDailyTotals {
  kcal: number
  protein: number
  carbs: number
  sugars: number
  fat: number
  sat_fat: number
  fibers: number
  missing_items: MealPlanMissingItem[]
}

export type MealPlanLineType = 'product' | 'recipe' | 'note'
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

  product_grocy_id: number | null
  product_amount: string | null
  product_amount_stock: string | null
  product_qu_id: number | null
  product_qu_name: string | null

  recipe_grocy_id: number | null
  recipe_servings: string | null

  note: string | null

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

  product_grocy_id?: number | null
  product_amount?: string | number | null
  product_amount_stock?: string | number | null
  product_qu_id?: number | null

  recipe_grocy_id?: number | null
  recipe_servings?: string | number | null

  note?: string | null
}

export interface MealPlanLineEdit {
  product_amount?: string | number | null
  product_amount_stock?: string | number | null
  recipe_servings?: string | number | null
  note?: string | null
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

export type DayCheckState = 'NONE' | 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE'

export type DayCheckOutcome =
  | 'insufficient_resolved_with_list'
  | 'insufficient_cancelled'

export interface DayCheckProductDetail {
  product_id: number
  name: string
  amount: number
  note: string
}

export interface DayCheckResult {
  status: 'success' | 'insufficient_stock'
  products_to_consume: Record<string, unknown>
  products_to_buy: Record<string, unknown>
  products_to_buy_detailed: DayCheckProductDetail[]
  products_to_consume_detailed: DayCheckProductDetail[]
  message: string
}

export interface DayCheckStatusResponse {
  state: DayCheckState
  task_id?: string | null
  step?: string | null
  date?: string | null
  created_at?: string | null
  result?: DayCheckResult | null
  error?: string | null
  outcome?: DayCheckOutcome | null
}

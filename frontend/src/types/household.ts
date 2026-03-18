export interface HouseholdMember {
  user_id: number
  username: string
  email: string
  role_name: string
  has_grocy_key: boolean
  last_products_sync_at: string | null
}

export interface HouseholdWithRole {
  id: number
  name: string
  grocy_url: string | null
  address: string | null
  role_name: string
}

export interface HouseholdDetail extends HouseholdWithRole {
  members: HouseholdMember[]
}

export interface UserSearchItem {
  id: number
  username: string
  email: string
}

export interface BackfillCounts {
  products: number
  recipes: number
  consumed_products: number
  recipes_data: number
  meal_plan_consumptions: number
  note_nutrients: number
  daily_nutrition: number
  total: number
}

export interface DataSummary {
  consumed_products: number
  recipes_data: number
  meal_plan_consumptions: number
  note_nutrients: number
  daily_nutrition: number
  total: number
}

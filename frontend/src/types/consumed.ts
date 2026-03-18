export interface ConsumedProductDetailItem {
  id: number
  product_name: string
  quantity: number
  recipe_grocy_id: number | null
  cost: number | null
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
}

export interface NoteDetailItem {
  id: number
  note: string | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

export interface ConsumedDayDetail {
  date: string
  products: ConsumedProductDetailItem[]
  notes: NoteDetailItem[]
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
  total_cost: number | null
}

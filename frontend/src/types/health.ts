export type Gender = 'male' | 'female'

export type ActivityLevel =
  | 'sedentary'
  | 'lightly_active'
  | 'moderately_active'
  | 'very_active'
  | 'extra_active'

export type Goal = 'maintain' | 'lose' | 'gain'

export interface HealthParameters {
  gender: Gender | null
  date_of_birth: string | null
  height: number | null
  weight: number | null
  activity_level: ActivityLevel | null
  goal: Goal | null
  calorie_deficit_percent: number | null
  daily_calories: number | null
  daily_proteins: number | null
  daily_fats: number | null
  daily_fats_saturated: number | null
  daily_carbohydrates: number | null
  daily_carbohydrates_of_sugars: number | null
  daily_salt: number | null
  daily_fibers: number | null
}

export const GENDER_LABELS: Record<Gender, string> = {
  male: 'Male',
  female: 'Female',
}

export const ACTIVITY_LEVEL_LABELS: Record<ActivityLevel, string> = {
  sedentary: 'Sedentary (1.2)',
  lightly_active: 'Lightly active (1.375)',
  moderately_active: 'Moderately active (1.55)',
  very_active: 'Very active (1.725)',
  extra_active: 'Extra active (1.9)',
}

export const GOAL_LABELS: Record<Goal, string> = {
  maintain: 'Maintain weight',
  lose: 'Lose weight',
  gain: 'Gain weight',
}

export const ACTIVITY_FACTORS: Record<ActivityLevel, number> = {
  sedentary: 1.2,
  lightly_active: 1.375,
  moderately_active: 1.55,
  very_active: 1.725,
  extra_active: 1.9,
}

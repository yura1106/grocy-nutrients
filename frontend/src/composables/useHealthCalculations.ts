import type { Gender, ActivityLevel, Goal } from '../types/health'
import { ACTIVITY_FACTORS } from '../types/health'

interface BMICategory {
  label: string
  color: string
}

interface Macros {
  daily_calories: number
  daily_proteins: number
  daily_fats: number
  daily_fats_saturated: number
  daily_carbohydrates: number
  daily_carbohydrates_of_sugars: number
  daily_salt: number
  daily_fibers: number
}

export function useHealthCalculations() {
  /**
   * Mifflin-St Jeor BMR equation.
   * Male:   10 * weight(kg) + 6.25 * height(cm) - 5 * age + 5
   * Female: 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 161
   */
  function calcBMR(weight: number, height: number, age: number, gender: Gender): number {
    const base = 10 * weight + 6.25 * height - 5 * age
    return gender === 'male' ? base + 5 : base - 161
  }

  function calcTDEE(bmr: number, activityLevel: ActivityLevel): number {
    return bmr * ACTIVITY_FACTORS[activityLevel]
  }

  function calcGoalCalories(tdee: number, goal: Goal): number {
    if (goal === 'lose') return tdee - 500
    if (goal === 'gain') return tdee + 500
    return tdee
  }

  function calcBMI(weight: number, heightCm: number): number {
    const heightM = heightCm / 100
    return weight / (heightM * heightM)
  }

  function getBMICategory(bmi: number): BMICategory {
    if (bmi < 16) return { label: 'Severe underweight', color: 'text-red-700 bg-red-50' }
    if (bmi < 18.5) return { label: 'Underweight', color: 'text-blue-600 bg-blue-50' }
    if (bmi < 25) return { label: 'Normal', color: 'text-green-600 bg-green-50' }
    if (bmi < 30) return { label: 'Overweight', color: 'text-orange-500 bg-orange-50' }
    return { label: 'Obesity', color: 'text-red-600 bg-red-50' }
  }

  /**
   * Macro distribution based on body weight and remaining calories.
   *
   * Proteins: per kg body weight (Morton et al., 2018 meta-analysis)
   *   - maintain: 1.6 g/kg
   *   - lose:     1.8 g/kg (higher to preserve muscle at deficit)
   *   - gain:     1.8 g/kg
   *
   * Remaining calories split:
   *   - Fats: 30% of total calories (1g = 9kcal)
   *   - Carbs: remaining calories (1g = 4kcal)
   *   - Saturated fats: max 10% of total (1g = 9kcal)
   *   - Sugars: max 10% of total (1g = 4kcal)
   *   - Salt: 5g (WHO)
   *   - Fiber: 25g (WHO)
   */
  function calcMacros(calories: number, weight: number, goal: Goal): Macros {
    const proteinPerKg = goal === 'maintain' ? 1.6 : 1.8
    const proteins = Math.round(weight * proteinPerKg)
    const proteinCal = proteins * 4

    const fatCal = calories * 0.30
    const fats = Math.round(fatCal / 9)

    const carbCal = Math.max(0, calories - proteinCal - fatCal)
    const carbs = Math.round(carbCal / 4)

    return {
      daily_calories: Math.round(calories),
      daily_proteins: proteins,
      daily_fats: fats,
      daily_fats_saturated: Math.round((calories * 0.10) / 9),
      daily_carbohydrates: carbs,
      daily_carbohydrates_of_sugars: Math.round((calories * 0.10) / 4),
      daily_salt: 5,
      daily_fibers: 25,
    }
  }

  function ageFromDOB(dob: string): number {
    const birth = new Date(dob)
    const today = new Date()
    let age = today.getFullYear() - birth.getFullYear()
    const m = today.getMonth() - birth.getMonth()
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
      age--
    }
    return age
  }

  return { calcBMR, calcTDEE, calcGoalCalories, calcBMI, getBMICategory, calcMacros, ageFromDOB }
}

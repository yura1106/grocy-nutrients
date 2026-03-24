import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useHealthCalculations } from '@/composables/useHealthCalculations'

vi.mock('axios')

describe('useHealthCalculations', () => {
  const { calcBMR, calcTDEE, calcGoalCalories, calcBMI, getBMICategory, calcMacros, ageFromDOB } =
    useHealthCalculations()

  describe('calcBMR', () => {
    it('calculates BMR for male', () => {
      // 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
      expect(calcBMR(80, 180, 30, 'male')).toBe(1780)
    })

    it('calculates BMR for female', () => {
      // 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
      expect(calcBMR(60, 165, 25, 'female')).toBe(1345.25)
    })
  })

  describe('calcTDEE', () => {
    it('multiplies BMR by activity factor', () => {
      expect(calcTDEE(1780, 'sedentary')).toBeCloseTo(2136)
      expect(calcTDEE(1780, 'moderately_active')).toBeCloseTo(2759)
    })
  })

  describe('calcGoalCalories', () => {
    it('returns TDEE for maintain', () => {
      expect(calcGoalCalories(2000, 'maintain')).toBe(2000)
    })

    it('subtracts 500 for lose', () => {
      expect(calcGoalCalories(2000, 'lose')).toBe(1500)
    })

    it('adds 500 for gain', () => {
      expect(calcGoalCalories(2000, 'gain')).toBe(2500)
    })
  })

  describe('calcBMI', () => {
    it('calculates BMI correctly', () => {
      // 75 / (1.80^2) = 75 / 3.24 ≈ 23.15
      expect(calcBMI(75, 180)).toBeCloseTo(23.15, 1)
    })

    it('calculates BMI for different values', () => {
      // 100 / (1.70^2) = 100 / 2.89 ≈ 34.60
      expect(calcBMI(100, 170)).toBeCloseTo(34.60, 1)
    })
  })

  describe('getBMICategory', () => {
    it('returns Severe underweight for BMI < 16', () => {
      const result = getBMICategory(15)
      expect(result.label).toBe('Severe underweight')
      expect(result.color).toContain('text-red-700')
    })

    it('returns Underweight for BMI 16-18.5', () => {
      const result = getBMICategory(17)
      expect(result.label).toBe('Underweight')
      expect(result.color).toContain('text-blue-600')
    })

    it('returns Normal for BMI 18.5-25', () => {
      const result = getBMICategory(22)
      expect(result.label).toBe('Normal')
      expect(result.color).toContain('text-green-600')
    })

    it('returns Overweight for BMI 25-30', () => {
      const result = getBMICategory(27)
      expect(result.label).toBe('Overweight')
      expect(result.color).toContain('text-orange-500')
    })

    it('returns Obesity for BMI >= 30', () => {
      const result = getBMICategory(35)
      expect(result.label).toBe('Obesity')
      expect(result.color).toContain('text-red-600')
    })
  })

  describe('calcMacros', () => {
    it('calculates proteins from body weight for maintain (1.6 g/kg)', () => {
      const macros = calcMacros(2000, 75, 'maintain')
      expect(macros.daily_calories).toBe(2000)
      expect(macros.daily_proteins).toBe(120) // 75 * 1.6
      expect(macros.daily_fats).toBe(67) // 2000*0.30/9
      expect(macros.daily_fats_saturated).toBe(22) // 2000*0.10/9
      // carbs = (2000 - 120*4 - 2000*0.30) / 4 = (2000 - 480 - 600) / 4 = 230
      expect(macros.daily_carbohydrates).toBe(230)
      expect(macros.daily_carbohydrates_of_sugars).toBe(50) // 2000*0.10/4
      expect(macros.daily_salt).toBe(5)
      expect(macros.daily_fibers).toBe(25)
    })

    it('uses higher protein coefficient for lose (1.8 g/kg)', () => {
      const macros = calcMacros(1500, 75, 'lose')
      expect(macros.daily_proteins).toBe(135) // 75 * 1.8
    })

    it('uses higher protein coefficient for gain (1.8 g/kg)', () => {
      const macros = calcMacros(2500, 75, 'gain')
      expect(macros.daily_proteins).toBe(135) // 75 * 1.8
    })
  })

  describe('ageFromDOB', () => {
    it('calculates age correctly', () => {
      const today = new Date()
      const birthYear = today.getFullYear() - 30
      const dob = `${birthYear}-01-01`
      expect(ageFromDOB(dob)).toBeGreaterThanOrEqual(29)
      expect(ageFromDOB(dob)).toBeLessThanOrEqual(30)
    })
  })
})

describe('HealthParameters component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('imports without error', async () => {
    const mod = await import('@/components/profile/HealthParameters.vue')
    expect(mod.default).toBeDefined()
  })
})

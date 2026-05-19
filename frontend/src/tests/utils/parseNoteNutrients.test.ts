import { describe, expect, it } from 'vitest'
import { parseNoteNutrients } from '@/utils/parseNoteNutrients'

describe('parseNoteNutrients', () => {
  it('parses full short format', () => {
    expect(
      parseNoteNutrients('Калорій:500/Білків:30/Вуглеводів:60/Жирів:15'),
    ).toEqual({
      kcal: 500,
      protein: 30,
      carbs: 60,
      fat: 15,
    })
  })

  it('parses extended keys (saturated, sugars, fibers)', () => {
    expect(
      parseNoteNutrients(
        'Калорій:750/Білків:40/Вуглеводів:50/Вуглеводів цукрів:5/Жирів:35/Жирів нас.:8/Клітковини:7',
      ),
    ).toEqual({
      kcal: 750,
      protein: 40,
      carbs: 50,
      sugars: 5,
      fat: 35,
      satFat: 8,
      fibers: 7,
    })
  })

  it('drops salt because daily totals do not track it', () => {
    expect(parseNoteNutrients('Солі:2.5/Калорій:200')).toEqual({ kcal: 200 })
  })

  it('returns empty for null/undefined/empty', () => {
    expect(parseNoteNutrients(null)).toEqual({})
    expect(parseNoteNutrients(undefined)).toEqual({})
    expect(parseNoteNutrients('')).toEqual({})
  })

  it('returns empty for plain text without format', () => {
    expect(parseNoteNutrients('просто текст про обід')).toEqual({})
  })

  it('handles whitespace around keys and values', () => {
    expect(parseNoteNutrients(' Калорій : 200 / Білків : 10 ')).toEqual({
      kcal: 200,
      protein: 10,
    })
  })

  it('skips malformed values', () => {
    expect(parseNoteNutrients('Калорій:abc/Білків:20')).toEqual({ protein: 20 })
  })

  it('keeps known keys mixed with unknown', () => {
    expect(parseNoteNutrients('Калорій:300/невідоме:1/Жирів:5')).toEqual({
      kcal: 300,
      fat: 5,
    })
  })

  it('parses float values', () => {
    expect(parseNoteNutrients('Калорій:250.5/Білків:12.75')).toEqual({
      kcal: 250.5,
      protein: 12.75,
    })
  })
})

import { formatQty } from './format.js'

export const SLOTS = ['breakfast', 'lunch', 'dinner']
export const slotLabel = (s) => s[0].toUpperCase() + s.slice(1)

const num = (v) => Number(v) || 0

// Rows from /plan/check that are short.
export const missingRows = (items = []) => items.filter((r) => num(r.missing) > 0)

// 'toor dal 40 g, peas 60 g'
export const describeMissing = (rows) => rows.map((r) => `${r.name} ${formatQty(r.missing, r.unit)}`).join(', ')

// meal_id -> that meal's check result
export function indexByMealId(check) {
  const m = new Map()
  ;((check && check.meals) || []).forEach((x) => m.set(x.meal_id, x))
  return m
}

// 'date|meal_type' -> meal
export function indexBySlot(meals = []) {
  const m = new Map()
  meals.forEach((x) => m.set(`${x.date}|${x.meal_type}`, x))
  return m
}

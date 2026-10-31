// Every call to the backend lives in this file. Pages never call fetch() directly.
// Owner: Role 3 (frontend).

const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

// One error type for the whole app. `status` 0 means the server could not be reached.
export class ApiError extends Error {
  constructor(message, status = 0, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail // raw FastAPI detail (string, list or object), for pages that need it
  }
}

// FastAPI sends errors as {detail: "text"} or {detail: [{msg: ...}, ...]} (422).
function detailToMessage(body, fallback) {
  const d = body && body.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).filter(Boolean).join('; ') || fallback
  if (d && typeof d === 'object' && typeof d.message === 'string') return d.message
  return fallback
}

export async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE + path)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
    })
  }

  let res
  try {
    res = await fetch(url, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('Could not reach the server. Is the backend running?', 0)
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    // empty or non-JSON body (for example 204): leave data as null
  }

  if (!res.ok) {
    throw new ApiError(detailToMessage(data, `Request failed (${res.status})`), res.status, data && data.detail)
  }
  return data
}

// --- Health (used by the server banner) ---
export const getHealth = () => request('/health')
export const getDbHealth = () => request('/health/db')

// --- Stock ---
export const listStock = () => request('/stock')

// Adding an ingredient that is already in stock ADDS to it (the backend merges).
export const addStock = ({ ingredient, quantity, unit, expiry_date }) =>
  request('/stock', {
    method: 'POST',
    body: { ingredient, quantity: Number(quantity), unit, expiry_date: expiry_date || null },
  })

// Editing SETS the exact amount. Note: the backend cannot clear an expiry date once set.
export const updateStock = (id, { quantity, unit, expiry_date }) =>
  request(`/stock/${id}`, {
    method: 'PATCH',
    body: { quantity: Number(quantity), unit, expiry_date: expiry_date || null },
  })

export const deleteStock = (id) => request(`/stock/${id}`, { method: 'DELETE' })

// Optional: GET /ingredients is not in the backend yet. If it is missing (404) we return [],
// and the page falls back to names already in stock.
export const listIngredients = async () => {
  try {
    return await request('/ingredients')
  } catch (e) {
    if (e.status === 404) return []
    throw e
  }
}

// --- Recipes ---
// The list has ingredient ids only (no names). Open one recipe to get names and scaled quantities.
export const listRecipes = () => request('/recipes')

// Quantities come back already scaled by the server, in base units (g / ml / count).
export const getRecipe = (id, servings) => request(`/recipes/${id}`, { params: { servings } })

const recipeBody = (v, nameKey) => ({
  name: v.name,
  meal_type: v.meal_type,
  base_servings: Number(v.base_servings),
  ingredients: v.ingredients.map((i) => ({
    [nameKey]: i.name,
    quantity: Number(i.quantity),
    unit: i.unit,
  })),
})

// Manual recipe: the backend field is `ingredient`.
export const createRecipe = (v) => request('/recipes', { method: 'POST', body: recipeBody(v, 'ingredient') })

// AI draft: ask for a draft (nothing is saved), then save the reviewed version. Field is `name`.
export const estimateRecipe = ({ dish_name, servings, meal_type }) =>
  request('/recipes/estimate', {
    method: 'POST',
    body: { dish_name, servings: Number(servings), meal_type: meal_type || null },
  })
export const saveEstimatedRecipe = (v) =>
  request('/recipes/estimate/save', { method: 'POST', body: recipeBody(v, 'name') })

// --- Plan, stock check, suggestions ---
// Returns { start_date, end_date, meals: [{ id, date, meal_type, recipe_id, recipe_name, servings, status }] }
export const getPlan = (start) => request('/plan', { params: { start } })

// Create or change one slot. Only send breakfast / lunch / dinner (the backend does not validate it).
export const putPlanMeal = (date, mealType, { recipe_id, servings }) =>
  request(`/plan/${date}/${mealType}`, {
    method: 'PUT',
    body: { recipe_id: Number(recipe_id), servings: Number(servings) },
  })

// scope: 'today' or 'week' (today + 6 days). Only meals still 'planned' are checked.
// Returns { scope, meals: [{ meal_id, date, meal_type, ok, items: [{ name, unit, needed, available, missing }] }],
//           summary: [...same item shape, summed over all meals], all_available }
export const getPlanCheck = (scope) => request('/plan/check', { params: { scope } })

// Returns { meal_id, already_done, deducted: [{ name, unit, quantity }], shortfalls: [{ name, unit, short_by }] }
export const markMealDone = (mealId) => request(`/meals/${mealId}/done`, { method: 'POST' })

export const getSuggestions = ({ date, meal_type }) => request('/suggestions', { params: { date, meal_type } })

// Endpoint helpers for shopping and audit are added in phase F5.

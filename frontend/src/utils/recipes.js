// Recipe form helpers. Pure functions, no API calls.

export const MEAL_TYPES = ['breakfast', 'lunch', 'dinner']

// Mirrors the backend's normalize_ingredient_name: lowercase, hyphens/underscores to spaces,
// punctuation removed, spaces collapsed. Unicode letters (Hindi names) are kept.
export function normalizeName(s) {
  return String(s || '')
    .trim()
    .toLowerCase()
    .replace(/[-_]/g, ' ')
    .replace(/[^\p{L}\p{N}_\s]/gu, '')
    .replace(/\s+/g, ' ')
}

// Set of normalized canonical names + aliases, or null when the ingredient list is unavailable.
export function buildKnownSet(ingredients) {
  const set = new Set()
  ;(ingredients || []).forEach((i) => {
    if (!i || !i.name) return
    set.add(normalizeName(i.name))
    ;(i.aliases || []).forEach((a) => set.add(normalizeName(a)))
  })
  return set.size > 0 ? set : null
}

export const blankRow = () => ({ name: '', quantity: '', unit: 'g' })

export const emptyRecipe = (servings = 4) => ({
  name: '',
  meal_type: 'lunch',
  base_servings: servings,
  ingredients: [blankRow()],
})

// Trim values and drop completely blank ingredient rows.
export function cleanRecipe(v) {
  return {
    name: String(v.name || '').trim(),
    meal_type: v.meal_type,
    base_servings: Number(v.base_servings),
    ingredients: (v.ingredients || [])
      .map((i) => ({
        name: String(i.name || '').trim(),
        quantity: String(i.quantity ?? '').trim(),
        unit: i.unit,
      }))
      .filter((i) => i.name || i.quantity !== ''),
  }
}

// Returns an error message, or null when the recipe looks fine to send.
export function validateRecipe(v, knownSet) {
  if (!v.name) return 'Give the recipe a name.'
  if (!MEAL_TYPES.includes(v.meal_type)) return 'Choose breakfast, lunch or dinner.'
  if (!Number.isInteger(v.base_servings) || v.base_servings < 1)
    return 'Servings must be a whole number of 1 or more.'
  if (v.ingredients.length === 0) return 'Add at least one ingredient.'
  const seen = new Set()
  for (let idx = 0; idx < v.ingredients.length; idx++) {
    const ing = v.ingredients[idx]
    if (!ing.name) return `Ingredient ${idx + 1} needs a name.`
    const q = Number(ing.quantity)
    if (ing.quantity === '' || !Number.isFinite(q) || q <= 0)
      return `Enter a quantity above 0 for ${ing.name}.`
    const key = normalizeName(ing.name)
    if (seen.has(key)) return `${ing.name} appears twice. Combine it into one line.`
    seen.add(key)
    if (knownSet && !knownSet.has(key)) return `'${ing.name}' is not in the ingredient list yet.`
  }
  return null
}

// The AI draft shape is not guaranteed, so read it defensively and fill gaps from what was asked.
export function normalizeDraft(raw, fallback) {
  const r = raw || {}
  const rows = Array.isArray(r.ingredients) ? r.ingredients : []
  return {
    name: r.name || r.dish_name || fallback.name || '',
    meal_type: MEAL_TYPES.includes(r.meal_type) ? r.meal_type : fallback.meal_type || 'lunch',
    base_servings: Number(r.base_servings || r.servings || fallback.servings || 2),
    ingredients: rows.map((i) => ({
      name: String(i.name || i.ingredient || ''),
      quantity: i.quantity === undefined || i.quantity === null ? '' : String(i.quantity),
      unit: i.unit || 'g',
    })),
  }
}

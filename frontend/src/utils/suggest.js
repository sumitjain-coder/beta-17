// The suggestion shape is read defensively: show whatever explanation the backend gives, never invent one.
const asText = (x) => {
  if (typeof x === 'string') return x
  if (x && typeof x === 'object') return String(x.text || x.reason || x.message || x.name || '')
  return ''
}

export function readSuggestion(s) {
  const r = s || {}
  let reasons = []
  if (Array.isArray(r.reasons)) reasons = r.reasons.map(asText)
  else if (typeof r.reasons === 'string') reasons = [r.reasons]
  else {
    const single = r.reason || r.explanation || r.why
    if (single) reasons = [asText(single)]
  }
  const missingRaw = r.missing ?? r.missing_ingredients ?? []
  const missing = Array.isArray(missingRaw) ? missingRaw.map(asText).filter(Boolean) : []
  return {
    id: r.recipe_id ?? r.id,
    name: r.recipe_name || r.name || 'Recipe',
    reasons: reasons.filter(Boolean),
    missing,
    score: typeof r.score === 'number' ? r.score : null,
  }
}

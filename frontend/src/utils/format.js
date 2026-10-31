// Display helpers shared by all pages. Pure functions, no API calls.

// Units the picker offers. Values must be accepted by the backend (units.py aliases).
export const UNIT_OPTIONS = [
  { value: 'g', label: 'g' },
  { value: 'kg', label: 'kg' },
  { value: 'ml', label: 'ml' },
  { value: 'l', label: 'litre' },
  { value: 'tsp', label: 'tsp' },
  { value: 'tbsp', label: 'tbsp' },
  { value: 'cup', label: 'cup' },
  { value: 'katori', label: 'katori' },
  { value: 'pinch', label: 'pinch' },
  { value: 'count', label: 'pieces' },
]

// "Low" rule for the badge, in base units. The backend has no threshold, so this is a
// simple display rule: under 100 g / 100 ml / 2 pieces.
export const LOW_AT = { g: 100, ml: 100, count: 2 }

const trim = (n, d = 2) => String(Number(n.toFixed(d)))

// 1500 g -> "1.5 kg", 250 ml -> "250 ml", 3 count -> "3 pcs"
export function formatQty(quantity, unit) {
  const q = Number(quantity)
  if (!Number.isFinite(q)) return '?'
  if (unit === 'g') return q >= 1000 ? `${trim(q / 1000)} kg` : `${trim(q, 1)} g`
  if (unit === 'ml') return q >= 1000 ? `${trim(q / 1000)} L` : `${trim(q, 1)} ml`
  if (unit === 'count') return `${trim(q, 1)} pcs`
  return `${trim(q)} ${unit}`
}

// Whole days from today to a 'YYYY-MM-DD' date (negative = already past). null if no date.
export function daysUntil(dateStr, today = new Date()) {
  if (!dateStr) return null
  const [y, m, d] = String(dateStr).slice(0, 10).split('-').map(Number)
  if (!y || !m || !d) return null
  const target = new Date(y, m - 1, d)
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((target - start) / 86400000)
}

export function expiryLabel(dateStr, today = new Date()) {
  const days = daysUntil(dateStr, today)
  if (days === null) return 'No expiry date'
  if (days < -1) return `Expired ${-days} days ago`
  if (days === -1) return 'Expired yesterday'
  if (days === 0) return 'Expires today'
  if (days === 1) return 'Expires tomorrow'
  if (days <= 7) return `Expires in ${days} days`
  const [y, m, d] = String(dateStr).slice(0, 10).split('-').map(Number)
  return `Expires ${new Date(y, m - 1, d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`
}

// { low: bool, expiry: 'expired' | 'soon' | null }  ('soon' = within 3 days)
export function stockStatus(item, today = new Date()) {
  const q = Number(item.quantity)
  const limit = LOW_AT[item.unit]
  const low = limit !== undefined && q <= limit
  const days = daysUntil(item.expiry_date, today)
  let expiry = null
  if (days !== null) expiry = days < 0 ? 'expired' : days <= 3 ? 'soon' : null
  return { low, expiry }
}

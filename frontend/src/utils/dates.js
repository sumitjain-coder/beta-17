// Local-date helpers. Dates travel to the backend as 'YYYY-MM-DD' strings.
const pad = (n) => String(n).padStart(2, '0')

export const toISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const todayISO = () => toISO(new Date())

export function parseISO(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function addDays(iso, n) {
  const d = parseISO(iso)
  d.setDate(d.getDate() + n)
  return toISO(d)
}

// 'Mon, 2 Nov'
export const dayLabel = (iso) =>
  parseISO(iso).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })

// 'Monday, 2 November'
export const longDayLabel = (iso) =>
  parseISO(iso).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })

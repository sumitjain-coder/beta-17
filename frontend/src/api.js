// Every call to the backend lives in this file. Pages never call fetch() directly.
// Owner: Role 3 (frontend).

const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

// One error type for the whole app. `status` 0 means the server could not be reached.
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// FastAPI sends errors as {detail: "text"} or {detail: [{msg: ...}, ...]} (422).
function detailToMessage(body, fallback) {
  const d = body && body.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).filter(Boolean).join('; ') || fallback
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
    throw new ApiError(detailToMessage(data, `Request failed (${res.status})`), res.status)
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

// Endpoint helpers for recipes, plan, shopping and audit are added in later phases.

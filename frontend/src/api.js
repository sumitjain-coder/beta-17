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

// Endpoint helpers are added per page in later phases (stock, recipes, plan, shopping, audit).

import { useState } from 'react'

// Household size is kept on this device only (localStorage) until the backend exposes it.
// It is just a number, no personal data. Used as the default servings in recipes and the planner.
const KEY = 'kitchensync.householdSize'

export function useHouseholdSize(defaultSize = 4) {
  const [size, setSize] = useState(() => {
    try {
      const v = Number(localStorage.getItem(KEY))
      return Number.isInteger(v) && v >= 1 && v <= 20 ? v : defaultSize
    } catch {
      return defaultSize
    }
  })

  function update(n) {
    const v = Math.min(20, Math.max(1, Math.round(Number(n) || defaultSize)))
    setSize(v)
    try {
      localStorage.setItem(KEY, String(v))
    } catch {
      // storage unavailable: keep the value in memory only
    }
  }

  return [size, update]
}

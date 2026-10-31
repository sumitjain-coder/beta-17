import { useRef, useState } from 'react'
import { UNIT_OPTIONS } from '../utils/format'
import { MEAL_TYPES, blankRow, cleanRecipe, validateRecipe } from '../utils/recipes'
import { ErrorBox, inputCls, btnPrimary, btnGhost } from './ui'
import Stepper from './Stepper'

// Used for both a manual recipe and a reviewed AI draft.
// onSubmit(cleanValues) must return a promise; if it throws, the message is shown here.
export default function RecipeForm({ initial, suggestNames, knownSet, submitLabel, onSubmit, onCancel, banner }) {
  const keyRef = useRef(0)
  const withKeys = (rows) => rows.map((r) => ({ ...r, _k: keyRef.current++ }))

  const [name, setName] = useState(initial.name)
  const [mealType, setMealType] = useState(initial.meal_type)
  const [servings, setServings] = useState(initial.base_servings)
  const [rows, setRows] = useState(() => withKeys(initial.ingredients.length ? initial.ingredients : [blankRow()]))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [missing, setMissing] = useState([])

  const setRow = (k, patch) => setRows((rs) => rs.map((r) => (r._k === k ? { ...r, ...patch } : r)))
  const addRow = () => setRows((rs) => [...rs, ...withKeys([blankRow()])])
  const removeRow = (k) => setRows((rs) => (rs.length > 1 ? rs.filter((r) => r._k !== k) : rs))

  async function submit(e) {
    e.preventDefault()
    const cleaned = cleanRecipe({ name, meal_type: mealType, base_servings: servings, ingredients: rows })
    const problem = validateRecipe(cleaned, knownSet)
    setMissing([])
    if (problem) return setError(problem)
    setError('')
    setBusy(true)
    try {
      await onSubmit(cleaned)
    } catch (err) {
      if (err && err.status >= 500) {
        setError(
          'The server could not save this recipe. A common cause is an ingredient name that is not in the database yet. Check the spelling, or ask a teammate to add the ingredient.'
        )
      } else {
        setError((err && err.message) || 'Something went wrong. Please try again.')
        const m = err && err.detail && err.detail.missing_ingredients
        setMissing(Array.isArray(m) ? m : [])
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-stone-200 bg-white p-4">
      {banner}
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="block text-sm sm:col-span-2">
          Recipe name
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Aloo paratha" />
        </label>
        <label className="block text-sm">
          Meal
          <select className={inputCls} value={mealType} onChange={(e) => setMealType(e.target.value)}>
            {MEAL_TYPES.map((m) => (
              <option key={m} value={m}>
                {m[0].toUpperCase() + m.slice(1)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="text-sm">
        <p className="mb-1">Quantities below are for this many servings</p>
        <Stepper value={servings} onChange={setServings} label="Servings the quantities are for" />
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">Ingredients</p>
        <datalist id="recipe-ingredient-names">
          {suggestNames.map((n) => (
            <option key={n} value={n} />
          ))}
        </datalist>
        {rows.map((r) => {
          const units = UNIT_OPTIONS.some((u) => u.value === r.unit)
            ? UNIT_OPTIONS
            : [...UNIT_OPTIONS, { value: r.unit, label: r.unit }]
          return (
            <div key={r._k} className="grid grid-cols-[1fr_6rem_6.5rem_auto] items-center gap-2">
              <input
                className={inputCls}
                list="recipe-ingredient-names"
                value={r.name}
                onChange={(e) => setRow(r._k, { name: e.target.value })}
                placeholder="Ingredient"
                aria-label="Ingredient name"
              />
              <input
                className={inputCls}
                type="number"
                inputMode="decimal"
                min="0"
                step="any"
                value={r.quantity}
                onChange={(e) => setRow(r._k, { quantity: e.target.value })}
                placeholder="Qty"
                aria-label="Quantity"
              />
              <select className={inputCls} value={r.unit} onChange={(e) => setRow(r._k, { unit: e.target.value })} aria-label="Unit">
                {units.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removeRow(r._k)}
                disabled={rows.length === 1}
                className={btnGhost}
                aria-label="Remove ingredient"
              >
                X
              </button>
            </div>
          )
        })}
        <button type="button" onClick={addRow} className={btnGhost}>
          + Add ingredient
        </button>
      </div>

      <ErrorBox message={error} />
      {missing.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">These ingredients are not in the database yet:</p>
          <ul className="mt-1 list-disc pl-5">
            {missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <p className="mt-1">Rename them to a known ingredient, or ask a teammate to add them.</p>
        </div>
      )}

      <div className="flex gap-2">
        <button type="submit" disabled={busy} className={btnPrimary}>
          {busy ? 'Saving...' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={busy} className={btnGhost}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

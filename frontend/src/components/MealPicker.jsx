import { useEffect, useMemo, useState } from 'react'
import { getSuggestions } from '../api'
import { readSuggestion } from '../utils/suggest'
import { slotLabel } from '../utils/plan'
import { dayLabel } from '../utils/dates'
import { Badge, ErrorBox, Loading, inputCls, btnPrimary, btnGhost } from './ui'
import Stepper from './Stepper'

// Choose a recipe and servings for one slot. Suggestions come from current stock;
// if they fail, the full recipe list below still works.
export default function MealPicker({
  date, mealType, recipes, defaultServings, initialRecipeId, initialServings, onSave, onCancel,
}) {
  const [servings, setServings] = useState(initialServings || defaultServings)
  const [selected, setSelected] = useState(initialRecipeId || null)
  const [query, setQuery] = useState('')
  const [showAll, setShowAll] = useState(false)
  const [sugg, setSugg] = useState({ loading: true, items: [], error: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setSugg({ loading: true, items: [], error: '' })
    getSuggestions({ date, meal_type: mealType })
      .then((res) => {
        const items = ((res && res.suggestions) || []).slice(0, 5).map(readSuggestion)
        if (alive) setSugg({ loading: false, items, error: '' })
      })
      .catch((e) => alive && setSugg({ loading: false, items: [], error: e.message }))
    return () => {
      alive = false
    }
  }, [date, mealType])

  const list = useMemo(() => {
    const q = query.trim().toLowerCase()
    return recipes
      .filter((r) => (showAll || r.meal_type === mealType) && (!q || r.name.toLowerCase().includes(q)))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [recipes, query, showAll, mealType])

  const selectedName =
    (recipes.find((r) => r.id === selected) || {}).name ||
    (sugg.items.find((s) => s.id === selected) || {}).name

  async function save() {
    if (!selected) return setError('Pick a recipe first.')
    setError('')
    setBusy(true)
    try {
      await onSave(selected, servings)
    } catch (e) {
      setError(e.message || 'Could not save this meal.')
      setBusy(false)
    }
  }

  const rowCls = (active) =>
    'w-full rounded-lg border px-3 py-2 text-left ' +
    (active ? 'border-emerald-500 bg-emerald-50' : 'border-stone-200 bg-white hover:bg-stone-50')

  return (
    <div className="space-y-4 rounded-xl border border-emerald-300 bg-emerald-50/40 p-4">
      <h3 className="font-semibold">
        {slotLabel(mealType)} on {dayLabel(date)}
      </h3>

      <div>
        <p className="mb-1 text-sm font-medium">Suggested from your stock</p>
        {sugg.loading ? (
          <Loading label="Looking at your stock..." />
        ) : sugg.error ? (
          <p className="text-sm text-stone-600">
            Suggestions are not available right now ({sugg.error}). Pick a recipe below instead.
          </p>
        ) : sugg.items.length === 0 ? (
          <p className="text-sm text-stone-600">No suggestions for this meal. Pick a recipe below.</p>
        ) : (
          <ul className="space-y-2">
            {sugg.items.map((s) => (
              <li key={s.id}>
                <button type="button" className={rowCls(selected === s.id)} onClick={() => setSelected(s.id)}>
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-medium">{s.name}</span>
                    {s.score !== null && <Badge tone="green">Score {Math.round(s.score)}</Badge>}
                  </span>
                  {s.reasons.map((r) => (
                    <span key={r} className="block text-sm text-stone-600">
                      {r}
                    </span>
                  ))}
                  {s.missing.length > 0 && (
                    <span className="block text-sm text-amber-800">Missing: {s.missing.join(', ')}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium">{showAll ? 'All recipes' : `${slotLabel(mealType)} recipes`}</p>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
            Show all meal types
          </label>
        </div>
        <input
          className={inputCls}
          placeholder="Search recipes..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search recipes"
        />
        <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto">
          {recipes.length === 0 ? (
            <li className="text-sm text-stone-600">No recipes yet. Add one on the Recipes page.</li>
          ) : list.length === 0 ? (
            <li className="text-sm text-stone-600">No recipes match.</li>
          ) : (
            list.map((r) => (
              <li key={r.id}>
                <button type="button" className={rowCls(selected === r.id)} onClick={() => setSelected(r.id)}>
                  {r.name}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="text-sm">
        <p className="mb-1">Servings</p>
        <Stepper value={servings} onChange={setServings} max={50} label="Servings" />
      </div>

      <ErrorBox message={error} />
      <div className="flex gap-2">
        <button className={btnPrimary} onClick={save} disabled={busy || !selected}>
          {busy ? 'Saving...' : selectedName ? `Plan ${selectedName}` : 'Plan this meal'}
        </button>
        <button className={btnGhost} onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  )
}

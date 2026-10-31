import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPlan, getPlanCheck, listRecipes, markMealDone, putPlanMeal } from '../api'
import { formatQty } from '../utils/format'
import { SLOTS, slotLabel, missingRows, describeMissing, indexByMealId } from '../utils/plan'
import { todayISO, longDayLabel } from '../utils/dates'
import { useHouseholdSize } from '../utils/household'
import { Badge, ErrorBox, Loading, btnPrimary, btnGhost } from '../components/ui'
import MealPicker from '../components/MealPicker'

export default function Today() {
  const today = todayISO()
  const [household] = useHouseholdSize()
  const [meals, setMeals] = useState([])
  const [check, setCheck] = useState(null)
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [checkError, setCheckError] = useState('')
  const [pickerSlot, setPickerSlot] = useState(null)
  const [results, setResults] = useState({}) // meal id -> mark-done result, kept for this session

  const load = useCallback(async () => {
    const [p, c] = await Promise.allSettled([getPlan(today), getPlanCheck('today')])
    if (p.status === 'fulfilled') {
      setMeals(p.value.meals.filter((m) => m.date === today))
      setError('')
    } else {
      setError(p.reason.message)
    }
    if (c.status === 'fulfilled') {
      setCheck(c.value)
      setCheckError('')
    } else {
      setCheck(null)
      setCheckError(c.reason.message)
    }
    setLoading(false)
  }, [today])

  useEffect(() => {
    load()
    listRecipes().then(setRecipes).catch(() => setRecipes([]))
  }, [load])

  const checks = useMemo(() => indexByMealId(check), [check])
  const shortToday = check ? missingRows(check.summary) : []

  async function savePick(slot, recipeId, servings) {
    await putPlanMeal(today, slot, { recipe_id: recipeId, servings })
    setPickerSlot(null)
    await load()
  }

  async function done(meal) {
    const res = await markMealDone(meal.id)
    setResults((r) => ({ ...r, [meal.id]: res }))
    await load()
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Today</h1>
        <p className="text-sm text-stone-600">{longDayLabel(today)}</p>
      </div>

      {checkError && <ErrorBox message={`Could not check stock: ${checkError}`} />}

      {check && check.meals.length > 0 && (
        <div
          className={
            'flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm ' +
            (shortToday.length ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900')
          }
        >
          {shortToday.length ? (
            <>
              <span>
                <strong>Short for today:</strong> {describeMissing(shortToday)}
              </span>
              <Link to="/shopping" className="font-medium underline">
                Open shopping list
              </Link>
            </>
          ) : (
            <span>Everything for today's planned meals is in stock.</span>
          )}
        </div>
      )}

      {loading ? (
        <Loading label="Loading today's meals..." />
      ) : error ? (
        <ErrorBox message={error} onRetry={load} />
      ) : (
        <div className="space-y-4">
          {SLOTS.map((slot) => {
            const meal = meals.find((m) => m.meal_type === slot)
            return (
              <section key={slot} className="space-y-2">
                {meal ? (
                  <MealCard
                    slot={slot}
                    meal={meal}
                    chk={checks.get(meal.id)}
                    checkFailed={Boolean(checkError)}
                    result={results[meal.id]}
                    onDone={() => done(meal)}
                    onChange={() => setPickerSlot(slot)}
                  />
                ) : (
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-dashed border-stone-300 bg-white px-4 py-4">
                    <div>
                      <p className="font-medium">{slotLabel(slot)}</p>
                      <p className="text-sm text-stone-500">Nothing planned yet.</p>
                    </div>
                    <button className={btnGhost} onClick={() => setPickerSlot(slot)}>
                      + Plan {slot}
                    </button>
                  </div>
                )}
                {pickerSlot === slot && (
                  <MealPicker
                    key={slot}
                    date={today}
                    mealType={slot}
                    recipes={recipes}
                    defaultServings={household}
                    initialRecipeId={meal && meal.recipe_id}
                    initialServings={meal && meal.servings}
                    onSave={(rid, sv) => savePick(slot, rid, sv)}
                    onCancel={() => setPickerSlot(null)}
                  />
                )}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}

function MealCard({ slot, meal, chk, checkFailed, result, onDone, onChange }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const isDone = meal.status === 'done'
  const items = chk ? [...chk.items].sort((a, b) => Number(b.missing > 0) - Number(a.missing > 0)) : []
  const short = missingRows(items)

  async function run() {
    setBusy(true)
    setError('')
    try {
      await onDone()
      setConfirming(false)
    } catch (e) {
      setError(e.message || 'Could not mark this meal as done.')
    } finally {
      setBusy(false)
    }
  }

  function press() {
    if (short.length > 0 && !confirming) return setConfirming(true)
    run()
  }

  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-stone-500">{slotLabel(slot)}</p>
          <p className="text-lg font-semibold">{meal.recipe_name}</p>
          <p className="text-sm text-stone-500">{meal.servings} servings</p>
        </div>
        {isDone ? <Badge tone="green">Done</Badge> : chk ? chk.ok ? <Badge tone="green">Ready to cook</Badge> : <Badge tone="amber">Short on {short.length}</Badge> : <Badge>Planned</Badge>}
      </div>

      {!isDone && short.length > 0 && (
        <div role="alert" className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <strong>Missing before you cook:</strong> {describeMissing(short)}
        </div>
      )}

      {!isDone && items.length > 0 && (
        <ul className="mt-3 divide-y divide-stone-100 text-sm">
          {items.map((r) => (
            <li key={r.ingredient_id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <span className="capitalize">{r.name}</span>
              <span className="text-stone-600">
                need {formatQty(r.needed, r.unit)}, have {formatQty(r.available, r.unit)}
                {Number(r.missing) > 0 && <span className="font-medium text-amber-800"> (short {formatQty(r.missing, r.unit)})</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
      {!isDone && !chk && checkFailed && (
        <p className="mt-3 text-sm text-stone-600">Stock check is unavailable, so quantities are not shown.</p>
      )}

      {result && <DoneResult result={result} />}
      <ErrorBox message={error} />

      {!isDone && (
        <div className="mt-3 space-y-2">
          {confirming && (
            <p className="text-sm text-amber-900">
              Some ingredients are short. Marking this meal done will use up what you have, and those items will go to
              zero. Continue?
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button className={btnPrimary} onClick={press} disabled={busy}>
              {busy ? 'Saving...' : confirming ? 'Mark done anyway' : 'Mark done'}
            </button>
            {confirming && (
              <button className={btnGhost} onClick={() => setConfirming(false)} disabled={busy}>
                Cancel
              </button>
            )}
            {!confirming && (
              <button className={btnGhost} onClick={onChange} disabled={busy}>
                Change meal
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function DoneResult({ result }) {
  if (result.already_done) {
    return (
      <p className="mt-3 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700">
        This meal was already marked done. Nothing was deducted again.
      </p>
    )
  }
  const used = result.deducted || []
  const short = result.shortfalls || []
  return (
    <div className="mt-3 space-y-2 text-sm">
      {used.length > 0 && (
        <p className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-900">
          <strong>Used from stock:</strong> {used.map((d) => `${d.name} ${formatQty(d.quantity, d.unit)}`).join(', ')}.
        </p>
      )}
      {short.length > 0 && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
          <strong>Stock ran short:</strong>{' '}
          {short.map((s) => `${s.name} by ${formatQty(s.short_by, s.unit)}`).join(', ')}. Those items are now at zero, so
          check your stock list.
        </p>
      )}
      {used.length === 0 && short.length === 0 && <p className="text-stone-600">Marked done. No ingredients needed stock.</p>}
    </div>
  )
}

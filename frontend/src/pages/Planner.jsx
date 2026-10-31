import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPlan, getPlanCheck, listRecipes, putPlanMeal } from '../api'
import { SLOTS, slotLabel, missingRows, describeMissing, indexByMealId, indexBySlot } from '../utils/plan'
import { todayISO, addDays, dayLabel } from '../utils/dates'
import { useHouseholdSize } from '../utils/household'
import { Badge, ErrorBox, Loading, btnGhost } from '../components/ui'
import MealPicker from '../components/MealPicker'

export default function Planner() {
  const today = todayISO()
  const [household] = useHouseholdSize()
  const [start, setStart] = useState(today)
  const [plan, setPlan] = useState(null)
  const [check, setCheck] = useState(null)
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [checkError, setCheckError] = useState('')
  const [picker, setPicker] = useState(null) // { date, mealType }

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(start, i)), [start])

  const load = useCallback(async () => {
    const [p, c] = await Promise.allSettled([getPlan(start), getPlanCheck('week')])
    if (p.status === 'fulfilled') {
      setPlan(p.value)
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
  }, [start])

  useEffect(() => {
    setLoading(true)
    load()
  }, [load])

  useEffect(() => {
    listRecipes().then(setRecipes).catch(() => setRecipes([]))
  }, [])

  const slots = useMemo(() => indexBySlot(plan ? plan.meals : []), [plan])
  const checks = useMemo(() => indexByMealId(check), [check])
  const toBuy = check ? missingRows(check.summary) : []
  const hasPlanned = check && check.meals.length > 0

  async function savePick(date, mealType, recipeId, servings) {
    await putPlanMeal(date, mealType, { recipe_id: recipeId, servings })
    setPicker(null)
    await load()
  }

  const rangeLabel = `${dayLabel(days[0])} to ${dayLabel(days[6])}`

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Weekly planner</h1>
          <p className="text-sm text-stone-600">{rangeLabel}</p>
        </div>
        <div className="flex gap-2">
          <button className={btnGhost} onClick={() => setStart(addDays(start, -7))}>
            Previous 7 days
          </button>
          <button className={btnGhost} onClick={() => setStart(today)} disabled={start === today}>
            Today
          </button>
          <button className={btnGhost} onClick={() => setStart(addDays(start, 7))}>
            Next 7 days
          </button>
        </div>
      </div>

      {checkError && (
        <ErrorBox message={`Could not check stock: ${checkError}. You can still plan meals.`} />
      )}

      {check && hasPlanned && (
        <div
          className={
            'flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm ' +
            (toBuy.length ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900')
          }
        >
          {toBuy.length ? (
            <>
              <span>
                <strong>To buy for the next 7 days:</strong> {describeMissing(toBuy)}
              </span>
              <Link to="/shopping" className="font-medium underline">
                Open shopping list
              </Link>
            </>
          ) : (
            <span>Everything for the planned meals in the next 7 days is in stock.</span>
          )}
        </div>
      )}

      {loading ? (
        <Loading label="Loading your plan..." />
      ) : error ? (
        <ErrorBox message={error} onRetry={load} />
      ) : (
        <div className="space-y-3">
          {days.map((date) => (
            <section key={date} className="rounded-xl border border-stone-200 bg-white p-3">
              <div className="mb-2 flex items-center gap-2">
                <h2 className="font-semibold">{dayLabel(date)}</h2>
                {date === today && <Badge tone="green">Today</Badge>}
              </div>
              <div className="grid gap-2 md:grid-cols-3">
                {SLOTS.map((slot) => (
                  <Slot
                    key={slot}
                    slot={slot}
                    meal={slots.get(`${date}|${slot}`)}
                    chk={checks.get((slots.get(`${date}|${slot}`) || {}).id)}
                    onPlan={() => setPicker({ date, mealType: slot })}
                  />
                ))}
              </div>
              {picker && picker.date === date && (
                <div className="mt-3">
                  <MealPicker
                    key={`${picker.date}-${picker.mealType}`}
                    date={picker.date}
                    mealType={picker.mealType}
                    recipes={recipes}
                    defaultServings={household}
                    initialRecipeId={(slots.get(`${date}|${picker.mealType}`) || {}).recipe_id}
                    initialServings={(slots.get(`${date}|${picker.mealType}`) || {}).servings}
                    onSave={(rid, sv) => savePick(picker.date, picker.mealType, rid, sv)}
                    onCancel={() => setPicker(null)}
                  />
                </div>
              )}
            </section>
          ))}
          <p className="text-xs text-stone-500">
            Stock status covers the next 7 days from today and is checked in date order, so earlier meals use stock first.
            Meals on other dates show as planned without a stock check.
          </p>
        </div>
      )}
    </div>
  )
}

function Slot({ slot, meal, chk, onPlan }) {
  const box = 'rounded-lg border border-stone-200 p-3'
  if (!meal) {
    return (
      <div className={box + ' flex flex-col justify-between gap-2'}>
        <p className="text-sm font-medium text-stone-500">{slotLabel(slot)}</p>
        <button className={btnGhost} onClick={onPlan}>
          + Plan
        </button>
      </div>
    )
  }
  const done = meal.status === 'done'
  const short = chk ? missingRows(chk.items) : []
  return (
    <div className={box + (done ? ' bg-stone-50' : '')}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-stone-500">{slotLabel(slot)}</p>
        {done ? (
          <Badge tone="green">Done</Badge>
        ) : chk ? (
          chk.ok ? (
            <Badge tone="green">Ready</Badge>
          ) : (
            <Badge tone="amber">Short on {short.length}</Badge>
          )
        ) : (
          <Badge>Planned</Badge>
        )}
      </div>
      <p className="mt-1 font-medium">{meal.recipe_name}</p>
      <p className="text-sm text-stone-500">{meal.servings} servings</p>
      {short.length > 0 && <p className="mt-1 text-sm text-amber-800">Short: {describeMissing(short)}</p>}
      {done ? (
        <p className="mt-2 text-xs text-stone-500">Cooked. Stock was already deducted.</p>
      ) : (
        <button className={btnGhost + ' mt-2'} onClick={onPlan}>
          Change
        </button>
      )}
    </div>
  )
}

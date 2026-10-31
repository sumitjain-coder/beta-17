import { useCallback, useEffect, useMemo, useState } from 'react'
import { listRecipes, getRecipe, createRecipe, saveEstimatedRecipe, listIngredients, listStock } from '../api'
import { formatQty } from '../utils/format'
import { MEAL_TYPES, buildKnownSet, emptyRecipe } from '../utils/recipes'
import { useHouseholdSize } from '../utils/household'
import { Badge, ErrorBox, SuccessBox, Loading, EmptyState, inputCls, btnPrimary, btnGhost } from '../components/ui'
import Stepper from '../components/Stepper'
import RecipeForm from '../components/RecipeForm'
import AiDraft from '../components/AiDraft'

const MEAL_TONE = { breakfast: 'amber', lunch: 'green', dinner: 'gray' }
const cap = (s) => s[0].toUpperCase() + s.slice(1)

export default function Recipes() {
  const [recipes, setRecipes] = useState([])
  const [ingredients, setIngredients] = useState([])
  const [stockNames, setStockNames] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [household, setHousehold] = useHouseholdSize()
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(null)
  const [mode, setMode] = useState(null) // null | 'manual' | 'ai'
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    setLoadError('')
    try {
      setRecipes(await listRecipes())
    } catch (e) {
      setLoadError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    listIngredients().then(setIngredients).catch(() => setIngredients([]))
    listStock().then((items) => setStockNames(items.map((i) => i.name))).catch(() => setStockNames([]))
  }, [load])

  // Strict checking only when the backend gives us the full ingredient list.
  const knownSet = useMemo(() => buildKnownSet(ingredients), [ingredients])
  const suggestNames = useMemo(() => {
    const names = new Set(stockNames)
    ingredients.forEach((i) => i && i.name && names.add(i.name))
    return [...names].sort()
  }, [ingredients, stockNames])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return recipes
      .filter((r) => (filter === 'all' || r.meal_type === filter) && (!q || r.name.toLowerCase().includes(q)))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [recipes, filter, query])

  async function afterSave(text) {
    setMode(null)
    setMessage(text)
    await load()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-2xl font-bold">Recipes</h1>
        <div className="text-sm">
          <p className="mb-1">Household size</p>
          <Stepper value={household} onChange={setHousehold} min={1} max={20} label="Household size" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button className={btnPrimary} onClick={() => setMode(mode === 'manual' ? null : 'manual')}>
          Add a recipe
        </button>
        <button className={btnGhost} onClick={() => setMode(mode === 'ai' ? null : 'ai')}>
          Ask AI to draft a recipe
        </button>
      </div>

      {mode === 'manual' && (
        <RecipeForm
          initial={emptyRecipe(household)}
          suggestNames={suggestNames}
          knownSet={knownSet}
          submitLabel="Save recipe"
          onSubmit={async (v) => {
            const r = await createRecipe(v)
            await afterSave(`Saved '${r.name}'.`)
          }}
          onCancel={() => setMode(null)}
        />
      )}
      {mode === 'ai' && (
        <AiDraft
          defaultServings={household}
          suggestNames={suggestNames}
          knownSet={knownSet}
          onSave={async (v) => {
            const r = await saveEstimatedRecipe(v)
            await afterSave(`Saved '${(r.recipe && r.recipe.name) || v.name}' (AI draft, reviewed by you).`)
          }}
          onManual={() => setMode('manual')}
          onCancel={() => setMode(null)}
        />
      )}

      <SuccessBox message={message} />

      <div className="flex flex-wrap items-center gap-2">
        {['all', ...MEAL_TYPES].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={
              'rounded-full px-4 py-1.5 text-sm font-medium ' +
              (filter === f ? 'bg-emerald-600 text-white' : 'border border-stone-300 text-stone-700 hover:bg-stone-100')
            }
          >
            {f === 'all' ? 'All' : cap(f)}
          </button>
        ))}
        <input
          className={inputCls + ' sm:ml-auto sm:max-w-xs'}
          placeholder="Search recipes..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search recipes"
        />
      </div>

      {loading ? (
        <Loading label="Loading recipes..." />
      ) : loadError ? (
        <ErrorBox message={loadError} onRetry={load} />
      ) : recipes.length === 0 ? (
        <EmptyState title="No recipes yet" hint="Add one above, or load the demo data." />
      ) : visible.length === 0 ? (
        <EmptyState title="No recipes match" hint="Try another meal type or search word." />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {visible.map((r) => {
            const open = openId === r.id
            return (
              <li
                key={r.id}
                className={'rounded-xl border bg-white ' + (open ? 'border-emerald-400 sm:col-span-2' : 'border-stone-200')}
              >
                <button
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                  onClick={() => setOpenId(open ? null : r.id)}
                  aria-expanded={open}
                >
                  <span>
                    <span className="block font-medium">{r.name}</span>
                    <span className="text-sm text-stone-500">
                      {r.ingredients.length} ingredients, written for {r.base_servings}
                    </span>
                  </span>
                  <Badge tone={MEAL_TONE[r.meal_type] || 'gray'}>{cap(r.meal_type)}</Badge>
                </button>
                {open && <RecipeDetail key={`${r.id}-${household}`} id={r.id} initialServings={household} />}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function RecipeDetail({ id, initialServings }) {
  const [servings, setServings] = useState(initialServings)
  const [state, setState] = useState({ loading: true, data: null, error: '' })

  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, error: '' }))
    getRecipe(id, servings)
      .then((data) => alive && setState({ loading: false, data, error: '' }))
      .catch((e) => alive && setState({ loading: false, data: null, error: e.message }))
    return () => {
      alive = false
    }
  }, [id, servings])

  const { loading, data, error } = state
  return (
    <div className="space-y-3 border-t border-stone-200 px-4 py-4">
      <div className="text-sm">
        <p className="mb-1">Servings</p>
        <Stepper value={servings} onChange={setServings} max={50} label="Servings to cook" />
      </div>
      {error && <ErrorBox message={error} />}
      {loading && !data && <Loading label="Calculating quantities..." />}
      {data && (
        <div className={loading ? 'opacity-60' : ''}>
          {data.ingredients.length === 0 ? (
            <p className="text-sm text-stone-500">This recipe has no ingredients saved.</p>
          ) : (
            <ul className="divide-y divide-stone-100">
              {data.ingredients.map((i) => (
                <li key={i.ingredient_id} className="flex justify-between py-2">
                  <span className="capitalize">{i.name}</span>
                  <span className="font-medium">{formatQty(i.quantity, i.unit)}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-stone-500">
            For {data.servings} servings. This recipe is written for {data.base_servings}; the server scales the quantities.
          </p>
        </div>
      )}
    </div>
  )
}

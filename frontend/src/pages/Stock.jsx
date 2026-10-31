import { useCallback, useEffect, useMemo, useState } from 'react'
import { listStock, addStock, updateStock, deleteStock, listIngredients } from '../api'
import { UNIT_OPTIONS, formatQty, expiryLabel, stockStatus } from '../utils/format'
import { Badge, ErrorBox, SuccessBox, Loading, EmptyState } from '../components/ui'

const inputCls =
  'w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-base focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500'
const btnPrimary =
  'rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-50'
const btnGhost =
  'rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50'

export default function Stock() {
  const [items, setItems] = useState([])
  const [ingredients, setIngredients] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [query, setQuery] = useState('')
  const [message, setMessage] = useState({ type: '', text: '' })
  const [busy, setBusy] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const load = useCallback(async () => {
    setLoadError('')
    try {
      setItems(await listStock())
    } catch (e) {
      setLoadError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    listIngredients().then(setIngredients).catch(() => setIngredients([]))
  }, [load])

  // Known ingredient names for autocomplete: the ingredient list plus anything already in stock.
  const knownNames = useMemo(() => {
    const names = new Set()
    ingredients.forEach((i) => i && i.name && names.add(i.name))
    items.forEach((i) => names.add(i.name))
    return [...names].sort()
  }, [ingredients, items])

  const baseUnitOf = useCallback(
    (name) => {
      const n = name.trim().toLowerCase()
      const fromStock = items.find((i) => i.name === n)
      if (fromStock) return fromStock.unit
      const fromList = ingredients.find((i) => i && i.name === n)
      return fromList ? fromList.base_unit : null
    },
    [items, ingredients]
  )

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items
      .filter((i) => !q || i.name.toLowerCase().includes(q))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [items, query])

  async function run(action) {
    setBusy(true)
    setMessage({ type: '', text: '' })
    try {
      return await action()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
      return null
    } finally {
      setBusy(false)
    }
  }

  async function handleAdd(values) {
    const row = await run(() => addStock(values))
    if (!row) return false
    await load()
    setMessage({
      type: 'ok',
      text: `${row.name} is now ${formatQty(row.quantity, row.unit)} in stock.`,
    })
    return true
  }

  async function handleSave(id, values) {
    const row = await run(() => updateStock(id, values))
    if (!row) return
    setEditingId(null)
    await load()
    setMessage({ type: 'ok', text: `${row.name} set to ${formatQty(row.quantity, row.unit)}.` })
  }

  async function handleDelete(item) {
    if (!window.confirm(`Remove ${item.name} from stock?`)) return
    const done = await run(async () => {
      await deleteStock(item.id)
      return true
    })
    if (!done) return
    await load()
    setMessage({ type: 'ok', text: `${item.name} removed from stock.` })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Kitchen stock</h1>

      <AddForm knownNames={knownNames} baseUnitOf={baseUnitOf} busy={busy} onAdd={handleAdd} />

      <ErrorBox message={message.type === 'error' ? message.text : ''} />
      <SuccessBox message={message.type === 'ok' ? message.text : ''} />

      <div>
        <input
          className={inputCls}
          placeholder="Search stock..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search stock"
        />
      </div>

      {loading ? (
        <Loading label="Loading stock..." />
      ) : loadError ? (
        <ErrorBox message={loadError} onRetry={load} />
      ) : items.length === 0 ? (
        <EmptyState
          title="Your kitchen stock is empty"
          hint="Add your first item above, for example 'rice', 2, kg."
        />
      ) : visible.length === 0 ? (
        <EmptyState title={`Nothing in stock matches '${query}'`} />
      ) : (
        <ul className="space-y-2">
          {visible.map((item) =>
            editingId === item.id ? (
              <EditRow
                key={item.id}
                item={item}
                busy={busy}
                onSave={(v) => handleSave(item.id, v)}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <ItemRow
                key={item.id}
                item={item}
                busy={busy}
                onEdit={() => setEditingId(item.id)}
                onDelete={() => handleDelete(item)}
              />
            )
          )}
        </ul>
      )}
    </div>
  )
}

function AddForm({ knownNames, baseUnitOf, busy, onAdd }) {
  const [name, setName] = useState('')
  const [quantity, setQuantity] = useState('')
  const [unit, setUnit] = useState('g')
  const [unitTouched, setUnitTouched] = useState(false)
  const [expiry, setExpiry] = useState('')
  const [formError, setFormError] = useState('')

  // When the typed name is a known ingredient, preselect its base unit (unless the user chose one).
  function changeName(value) {
    setName(value)
    if (!unitTouched) {
      const base = baseUnitOf(value)
      if (base) setUnit(base)
    }
  }

  async function submit(e) {
    e.preventDefault()
    if (!name.trim()) return setFormError('Enter an ingredient name.')
    if (!(Number(quantity) > 0)) return setFormError('Enter a quantity greater than 0.')
    setFormError('')
    const ok = await onAdd({ ingredient: name.trim(), quantity, unit, expiry_date: expiry })
    if (ok) {
      setName('')
      setQuantity('')
      setExpiry('')
      setUnitTouched(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-stone-200 bg-white p-4">
      <h2 className="font-semibold">Add to stock</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block text-sm">
          Ingredient
          <input
            className={inputCls}
            list="ingredient-names"
            value={name}
            onChange={(e) => changeName(e.target.value)}
            placeholder="e.g. toor dal"
          />
          <datalist id="ingredient-names">
            {knownNames.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
        </label>
        <label className="block text-sm">
          Quantity
          <input
            className={inputCls}
            type="number"
            inputMode="decimal"
            min="0"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Unit
          <select
            className={inputCls}
            value={unit}
            onChange={(e) => {
              setUnit(e.target.value)
              setUnitTouched(true)
            }}
          >
            {UNIT_OPTIONS.map((u) => (
              <option key={u.value} value={u.value}>
                {u.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Expiry (optional)
          <input className={inputCls} type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
        </label>
      </div>
      {formError && <p className="text-sm text-red-700">{formError}</p>}
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy} className={btnPrimary}>
          {busy ? 'Saving...' : 'Add to stock'}
        </button>
        <p className="text-xs text-stone-500">
          Adding an item that is already in stock increases it. Use Edit to set an exact amount.
        </p>
      </div>
    </form>
  )
}

function ItemRow({ item, busy, onEdit, onDelete }) {
  const { low, expiry } = stockStatus(item)
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white px-4 py-3">
      <div>
        <p className="font-medium capitalize">{item.name}</p>
        <p className="text-sm text-stone-500">{expiryLabel(item.expiry_date)}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {low && <Badge tone="amber">Low</Badge>}
        {expiry === 'expired' && <Badge tone="red">Expired</Badge>}
        {expiry === 'soon' && <Badge tone="amber">Expires soon</Badge>}
        <span className="min-w-20 text-right text-lg font-semibold">{formatQty(item.quantity, item.unit)}</span>
        <button onClick={onEdit} disabled={busy} className={btnGhost}>
          Edit
        </button>
        <button onClick={onDelete} disabled={busy} className={btnGhost}>
          Delete
        </button>
      </div>
    </li>
  )
}

function EditRow({ item, busy, onSave, onCancel }) {
  // Start from the stored base-unit amount so no conversion happens unless the user picks another unit.
  const [quantity, setQuantity] = useState(String(Number(Number(item.quantity).toFixed(3))))
  const [unit, setUnit] = useState(item.unit)
  const [expiry, setExpiry] = useState(item.expiry_date ? String(item.expiry_date).slice(0, 10) : '')
  const [error, setError] = useState('')

  function submit(e) {
    e.preventDefault()
    if (quantity === '' || !(Number(quantity) >= 0)) return setError('Enter a quantity of 0 or more.')
    setError('')
    onSave({ quantity, unit, expiry_date: expiry })
  }

  return (
    <li className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3">
      <form onSubmit={submit} className="space-y-3">
        <p className="font-medium capitalize">Editing {item.name}</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-sm">
            Exact amount
            <input
              className={inputCls}
              type="number"
              inputMode="decimal"
              min="0"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Unit
            <select className={inputCls} value={unit} onChange={(e) => setUnit(e.target.value)}>
              {UNIT_OPTIONS.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Expiry
            <input className={inputCls} type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
          </label>
        </div>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <div className="flex gap-2">
          <button type="submit" disabled={busy} className={btnPrimary}>
            {busy ? 'Saving...' : 'Save'}
          </button>
          <button type="button" onClick={onCancel} disabled={busy} className={btnGhost}>
            Cancel
          </button>
        </div>
      </form>
    </li>
  )
}

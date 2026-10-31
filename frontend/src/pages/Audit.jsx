import { useCallback, useEffect, useState } from 'react'
import { getAuditPick, getAuditHistory, submitAudit } from '../api'
import { UNIT_OPTIONS, formatQty } from '../utils/format'
import { Badge, ErrorBox, Loading, EmptyState, inputCls, btnPrimary, btnGhost } from '../components/ui'

const pct = (v) => (v === null || v === undefined ? 'n/a' : `${v}%`)

// Real amount minus what the app expected, as words. Uses the numbers, not the sign of the backend gap.
function gapText(item) {
  const diff = Number(item.actual) - Number(item.expected)
  if (Math.abs(diff) < 0.0005) return 'No gap'
  const amount = formatQty(Math.abs(diff), item.unit)
  return diff < 0 ? `App showed ${amount} too much` : `App showed ${amount} too little`
}

export default function Audit() {
  const [pick, setPick] = useState(null)
  const [history, setHistory] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [historyError, setHistoryError] = useState('')

  const load = useCallback(async () => {
    const [p, h] = await Promise.allSettled([getAuditPick(), getAuditHistory()])
    if (p.status === 'fulfilled') {
      setPick(p.value)
      setError('')
    } else {
      setPick(null)
      setError(p.reason.message)
    }
    if (h.status === 'fulfilled') {
      setHistory(h.value)
      setHistoryError('')
    } else {
      setHistory(null)
      setHistoryError(h.reason.message)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleSubmit(entries) {
    const res = await submitAudit(entries) // throws ApiError: the form shows the message
    setResult(res)
    const h = await getAuditHistory().catch(() => null)
    if (h) setHistory(h)
    return res
  }

  function startNew() {
    setResult(null)
    setLoading(true)
    load()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Weekly stock check</h1>
        <p className="text-sm text-stone-600">
          Look at a few items in the kitchen and enter what is really there. The app corrects its stock and shows how
          far off it was.
        </p>
      </div>

      {loading ? (
        <Loading label="Choosing items to check..." />
      ) : result ? (
        <Result result={result} onNew={startNew} />
      ) : error ? (
        <ErrorBox message={error} onRetry={load} />
      ) : pick && pick.items.length === 0 ? (
        <EmptyState title="No stock to check yet" hint={pick.message || 'Add items on the Stock page first.'} />
      ) : (
        pick && <CheckForm pick={pick} onSubmit={handleSubmit} />
      )}

      {!loading && <History history={history} error={historyError} />}
    </div>
  )
}

function CheckForm({ pick, onSubmit }) {
  const [values, setValues] = useState(() =>
    Object.fromEntries(pick.items.map((i) => [i.ingredient_id, { quantity: '', unit: i.unit }]))
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const set = (id, patch) => setValues((v) => ({ ...v, [id]: { ...v[id], ...patch } }))

  async function submit(e) {
    e.preventDefault()
    const entries = []
    for (const item of pick.items) {
      const v = values[item.ingredient_id]
      if (v.quantity === '') continue // left blank: not checked this time
      if (!(Number(v.quantity) >= 0)) return setError(`Enter 0 or more for ${item.name}.`)
      entries.push({ ingredient_id: item.ingredient_id, quantity: Number(v.quantity), unit: v.unit })
    }
    if (entries.length === 0) return setError('Enter the real amount for at least one item.')
    setError('')
    setBusy(true)
    try {
      await onSubmit(entries)
    } catch (err) {
      setError(err.message || 'Could not save the check.')
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      {pick.message && <p className="text-sm text-stone-600">{pick.message}</p>}
      <ul className="space-y-3">
        {pick.items.map((item) => {
          const v = values[item.ingredient_id]
          return (
            <li key={item.ingredient_id} className="space-y-2 rounded-xl border border-stone-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold capitalize">{item.name}</p>
                  <p className="text-sm text-stone-500">{item.reason}</p>
                </div>
                <span className="text-sm text-stone-600">App shows {formatQty(item.expected, item.unit)}</span>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:max-w-sm">
                <label className="block text-sm">
                  Real amount
                  <input
                    className={inputCls}
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="any"
                    value={v.quantity}
                    onChange={(e) => set(item.ingredient_id, { quantity: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Unit
                  <select
                    className={inputCls}
                    value={v.unit}
                    onChange={(e) => set(item.ingredient_id, { unit: e.target.value })}
                  >
                    {UNIT_OPTIONS.map((u) => (
                      <option key={u.value} value={u.value}>
                        {u.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </li>
          )
        })}
      </ul>

      <ErrorBox message={error} />
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className={btnPrimary} disabled={busy}>
          {busy ? 'Saving...' : 'Save check and correct stock'}
        </button>
        <p className="text-xs text-stone-500">Items you leave blank are skipped. Stock is set to what you enter.</p>
      </div>
      {pick.tolerance_note && <p className="text-xs text-stone-500">{pick.tolerance_note}</p>}
    </form>
  )
}

function Result({ result, onNew }) {
  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-lg font-semibold text-emerald-900">
          {result.matched} of {result.total} items matched ({pct(result.accuracy_pct)})
        </p>
        <p className="mt-1 text-sm text-emerald-900">
          Average error was <strong>{pct(result.avg_error_pct_before)}</strong> before the check and is{' '}
          <strong>{pct(result.avg_error_pct_after)}</strong> now, because stock was set to what you counted.
        </p>
      </div>

      <ul className="space-y-2">
        {result.items.map((i) => (
          <li key={i.ingredient_id} className="rounded-xl border border-stone-200 bg-white px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium capitalize">{i.name}</p>
              {i.matched ? <Badge tone="green">Matched</Badge> : <Badge tone="amber">Off by {pct(i.pct_error)}</Badge>}
            </div>
            <p className="mt-1 text-sm text-stone-600">
              Expected {formatQty(i.expected, i.unit)}, real {formatQty(i.actual, i.unit)}.{' '}
              {i.matched ? '' : gapText(i) + '.'} Stock is now {formatQty(i.stock_after, i.unit)}.
            </p>
          </li>
        ))}
      </ul>

      {result.tolerance_note && <p className="text-xs text-stone-500">{result.tolerance_note}</p>}
      <button className={btnGhost} onClick={onNew}>
        Start another check
      </button>
    </section>
  )
}

function History({ history, error }) {
  if (error) return <ErrorBox message={`Could not load past checks: ${error}`} />
  if (!history) return null
  const { audits = [], drift_ranking: drift = [] } = history
  if (audits.length === 0) return null

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Which items drift most</h2>
        {drift.length === 0 ? (
          <p className="text-sm text-stone-600">Not enough checks yet to rank items.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {drift.slice(0, 5).map((d) => (
              <li key={d.ingredient_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 bg-white px-4 py-3">
                <span>
                  <span className="font-medium capitalize">{d.name}</span>
                  <span className="text-sm text-stone-500">
                    {' '}
                    · off by {pct(d.avg_error_pct)} on average over {d.audits} check{d.audits === 1 ? '' : 's'}
                  </span>
                </span>
                <Badge tone="amber">{d.direction}</Badge>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-stone-500">
          "List too high" usually means meals were cooked without pressing Mark done. "List too low" usually means
          groceries were bought but not added to stock.
        </p>
      </div>

      <div>
        <h2 className="text-lg font-semibold">Past checks</h2>
        <ul className="mt-2 space-y-2">
          {audits.map((a) => (
            <li key={a.audit_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm">
              <span className="font-medium">{String(a.audit_date).slice(0, 10)}</span>
              <span className="text-stone-600">
                {a.matched} of {a.total} matched · average error {pct(a.avg_error_pct_before)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

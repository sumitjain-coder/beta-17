import { useCallback, useEffect, useRef, useState } from 'react'
import { generateShopping, getShopping, getShoppingHandoff, setShoppingChecked } from '../api'
import { todayISO, addDays, parseISO, toISO, dayLabel } from '../utils/dates'
import { Badge, ErrorBox, SuccessBox, Loading, EmptyState, btnPrimary, btnGhost } from '../components/ui'

// Monday of the week that contains `iso` (the backend snaps to Monday too).
function mondayOf(iso) {
  const d = parseISO(iso)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return toISO(d)
}

export default function Shopping() {
  const today = todayISO()
  const [weekStart, setWeekStart] = useState(() => mondayOf(today))
  const [items, setItems] = useState([])
  const [handoff, setHandoff] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [handoffError, setHandoffError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    const [l, h] = await Promise.allSettled([getShopping(weekStart), getShoppingHandoff(weekStart)])
    if (l.status === 'fulfilled') {
      setItems(l.value.items || [])
      setError('')
    } else {
      setItems([])
      setError(l.reason.message)
    }
    if (h.status === 'fulfilled') {
      setHandoff(h.value)
      setHandoffError('')
    } else {
      setHandoff(null)
      setHandoffError(h.reason.message)
    }
    setLoading(false)
  }, [weekStart])

  useEffect(() => {
    setLoading(true)
    setNotice('')
    load()
  }, [load])

  async function generate() {
    setBusy(true)
    setNotice('')
    setError('')
    try {
      const res = await generateShopping(weekStart)
      setNotice(
        res.items.length
          ? `List updated: ${res.items.length} item${res.items.length === 1 ? '' : 's'} to buy.`
          : 'Nothing is missing for the planned meals, so there is nothing to buy.'
      )
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function toggle(item) {
    setBusyId(item.id)
    setError('')
    try {
      await setShoppingChecked(item.id, !item.checked)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyId(null)
    }
  }

  const todo = items.filter((i) => !i.checked)
  const isThisWeek = weekStart === mondayOf(today)

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Shopping list</h1>
          <p className="text-sm text-stone-600">
            Week of {dayLabel(weekStart)} · built from the meals you planned, minus what is in stock
          </p>
        </div>
        <div className="flex gap-2">
          <button className={btnGhost} onClick={() => setWeekStart(addDays(weekStart, -7))}>
            Previous week
          </button>
          <button className={btnGhost} onClick={() => setWeekStart(mondayOf(today))} disabled={isThisWeek}>
            This week
          </button>
          <button className={btnGhost} onClick={() => setWeekStart(addDays(weekStart, 7))}>
            Next week
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button className={btnPrimary} onClick={generate} disabled={busy}>
          {busy ? 'Working...' : items.length ? 'Refresh list from plan' : 'Build list from plan'}
        </button>
        <p className="text-xs text-stone-500">
          Refreshing keeps what you ticked and updates quantities. Meals before today are not included.
        </p>
      </div>

      <ErrorBox message={error} onRetry={load} />
      <SuccessBox message={notice} />

      {loading ? (
        <Loading label="Loading shopping list..." />
      ) : items.length === 0 ? (
        <EmptyState
          title="No shopping list for this week yet"
          hint="Plan some meals, then press 'Build list from plan'. Only missing ingredients are added."
        />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className={
                'flex items-center justify-between gap-3 rounded-xl border px-4 py-3 ' +
                (item.checked ? 'border-stone-200 bg-stone-50' : 'border-stone-200 bg-white')
              }
            >
              <label className="flex min-h-11 flex-1 cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  className="h-6 w-6 accent-emerald-600"
                  checked={item.checked}
                  disabled={busyId === item.id}
                  onChange={() => toggle(item)}
                />
                <span className={'capitalize ' + (item.checked ? 'text-stone-400 line-through' : 'font-medium')}>
                  {item.name}
                </span>
              </label>
              <span className="flex items-center gap-2">
                {item.checked && <Badge tone="green">Bought</Badge>}
                <span className="text-lg font-semibold">{item.quantity_text}</span>
              </span>
            </li>
          ))}
        </ul>
      )}

      {!loading && items.length > 0 && (
        <Handoff handoff={handoff} error={handoffError} remaining={todo.length} />
      )}
    </div>
  )
}

function Handoff({ handoff, error, remaining }) {
  const [appKey, setAppKey] = useState(null)
  const [copied, setCopied] = useState(false)
  const areaRef = useRef(null)

  if (error) {
    return <ErrorBox message={`Could not prepare the hand-off: ${error}`} />
  }
  if (!handoff) return null

  if (handoff.count === 0) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        {handoff.message || 'Everything on the list is ticked off.'}
      </div>
    )
  }

  const activeKey = appKey || (handoff.apps[0] && handoff.apps[0].key)
  const activeApp = handoff.apps.find((a) => a.key === activeKey)

  async function copy() {
    try {
      await navigator.clipboard.writeText(handoff.text)
      setCopied(true)
    } catch {
      // Clipboard blocked (for example plain http on a phone): select the text so the user can copy it.
      if (areaRef.current) {
        areaRef.current.focus()
        areaRef.current.select()
      }
      setCopied(false)
    }
  }

  return (
    <section className="space-y-4 rounded-xl border border-stone-200 bg-white p-4">
      <div>
        <h2 className="font-semibold">Order what is missing</h2>
        <p className="text-sm text-stone-600">{remaining} item{remaining === 1 ? '' : 's'} left to buy.</p>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        {handoff.note}
      </div>

      <div className="space-y-2">
        <textarea
          ref={areaRef}
          readOnly
          rows={Math.min(10, handoff.count + 2)}
          value={handoff.text}
          aria-label="Shopping list text"
          className="w-full rounded-lg border border-stone-300 bg-stone-50 px-3 py-2 text-sm"
        />
        <div className="flex flex-wrap items-center gap-2">
          <button className={btnPrimary} onClick={copy}>
            {copied ? 'Copied' : 'Copy list'}
          </button>
          {handoff.whatsapp_link && (
            <a
              href={handoff.whatsapp_link}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-stone-300 px-4 py-2 font-medium text-stone-700 hover:bg-stone-100"
            >
              Share on WhatsApp
            </a>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">Search each item in an app</p>
        <div className="flex flex-wrap gap-2" role="tablist">
          {handoff.apps.map((a) => (
            <button
              key={a.key}
              role="tab"
              aria-selected={a.key === activeKey}
              onClick={() => setAppKey(a.key)}
              className={
                'rounded-lg px-3 py-2 text-sm font-medium ' +
                (a.key === activeKey ? 'bg-emerald-600 text-white' : 'border border-stone-300 text-stone-700 hover:bg-stone-100')
              }
            >
              {a.name}
            </button>
          ))}
        </div>
        <ul className="divide-y divide-stone-100">
          {handoff.items.map((i) => (
            <li key={i.id} className="flex min-h-11 items-center justify-between gap-3 py-2">
              <span>
                <span className="capitalize">{i.name}</span>
                <span className="text-stone-500"> · {i.quantity_text}</span>
              </span>
              <a
                href={i.links[activeKey]}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 rounded-lg border border-emerald-600 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50"
              >
                Search on {activeApp ? activeApp.name : 'app'}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

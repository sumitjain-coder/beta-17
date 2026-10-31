// Small shared pieces used by several pages.

const TONES = {
  gray: 'bg-stone-100 text-stone-700',
  green: 'bg-emerald-100 text-emerald-800',
  amber: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-800',
}

export function Badge({ tone = 'gray', children }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  )
}

export function ErrorBox({ message, onRetry }) {
  if (!message) return null
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <span>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="shrink-0 rounded-md border border-red-300 px-3 py-1 font-medium hover:bg-red-100">
          Try again
        </button>
      )}
    </div>
  )
}

export function SuccessBox({ message }) {
  if (!message) return null
  return (
    <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      {message}
    </div>
  )
}

export function Loading({ label = 'Loading...' }) {
  return <p className="py-8 text-center text-stone-500">{label}</p>
}

export function EmptyState({ title, hint }) {
  return (
    <div className="rounded-lg border border-dashed border-stone-300 px-4 py-10 text-center">
      <p className="font-medium text-stone-700">{title}</p>
      {hint && <p className="mt-1 text-sm text-stone-500">{hint}</p>}
    </div>
  )
}

// Shared Tailwind class strings for form controls and buttons.
export const inputCls =
  'w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-base focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500'
export const btnPrimary =
  'rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-50'
export const btnGhost =
  'rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50'

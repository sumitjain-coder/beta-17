// - [ 4 ] + control for whole numbers (servings, household size).
export default function Stepper({ value, onChange, min = 1, max = 50, label }) {
  const set = (n) => onChange(Math.min(max, Math.max(min, n)))
  const btn =
    'h-10 w-10 rounded-lg border border-stone-300 bg-white text-lg font-semibold text-stone-700 hover:bg-stone-100 disabled:opacity-40'
  return (
    <div className="inline-flex items-center gap-2" role="group" aria-label={label}>
      <button type="button" className={btn} onClick={() => set(value - 1)} disabled={value <= min} aria-label="Decrease">
        -
      </button>
      <span className="min-w-8 text-center text-lg font-semibold" aria-live="polite">
        {value}
      </span>
      <button type="button" className={btn} onClick={() => set(value + 1)} disabled={value >= max} aria-label="Increase">
        +
      </button>
    </div>
  )
}

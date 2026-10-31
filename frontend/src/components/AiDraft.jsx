import { useState } from 'react'
import { estimateRecipe } from '../api'
import { MEAL_TYPES, normalizeDraft } from '../utils/recipes'
import { ErrorBox, inputCls, btnPrimary, btnGhost } from './ui'
import Stepper from './Stepper'
import RecipeForm from './RecipeForm'

// Ask the AI for a draft recipe, then let the user edit and save it.
// Nothing is saved until the user presses Save, and quantities are never trusted blindly.
export default function AiDraft({ defaultServings, suggestNames, knownSet, onSave, onManual, onCancel }) {
  const [dish, setDish] = useState('')
  const [servings, setServings] = useState(defaultServings)
  const [mealType, setMealType] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState(null)

  async function generate(e) {
    e.preventDefault()
    if (!dish.trim()) return setError('Enter the name of a dish.')
    setError('')
    setDraft(null)
    setLoading(true)
    try {
      const res = await estimateRecipe({ dish_name: dish.trim(), servings, meal_type: mealType })
      setDraft(normalizeDraft(res && res.recipe, { name: dish.trim(), meal_type: mealType, servings }))
    } catch (err) {
      setError(err.message || 'The AI helper is not available right now.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={generate} className="space-y-3 rounded-xl border border-stone-200 bg-white p-4">
        <h2 className="font-semibold">Ask AI to draft a recipe</h2>
        <p className="text-sm text-stone-600">
          Use this for a dish that is not in the library. The AI only proposes a draft. You review and edit it before
          anything is saved.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-sm sm:col-span-2">
            Dish
            <input className={inputCls} value={dish} onChange={(e) => setDish(e.target.value)} placeholder="e.g. Lauki sabzi" />
          </label>
          <label className="block text-sm">
            Meal (optional)
            <select className={inputCls} value={mealType} onChange={(e) => setMealType(e.target.value)}>
              <option value="">Any</option>
              {MEAL_TYPES.map((m) => (
                <option key={m} value={m}>
                  {m[0].toUpperCase() + m.slice(1)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="text-sm">
          <p className="mb-1">Servings</p>
          <Stepper value={servings} onChange={setServings} label="Servings for the draft" />
        </div>

        <ErrorBox message={error} />
        {error && (
          <p className="text-sm text-stone-600">
            No AI data is available for this dish.{' '}
            <button type="button" onClick={onManual} className="font-medium text-emerald-700 underline">
              Enter the ingredients manually
            </button>{' '}
            instead.
          </p>
        )}

        <div className="flex gap-2">
          <button type="submit" disabled={loading} className={btnPrimary}>
            {loading ? 'Asking the AI...' : 'Generate draft'}
          </button>
          <button type="button" onClick={onCancel} disabled={loading} className={btnGhost}>
            Cancel
          </button>
        </div>
      </form>

      {draft && (
        <RecipeForm
          key={`${draft.name}-${draft.ingredients.length}`}
          initial={draft}
          suggestNames={suggestNames}
          knownSet={knownSet}
          submitLabel="Save recipe"
          onSubmit={onSave}
          onCancel={() => setDraft(null)}
          banner={
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-medium">AI draft. Please check every quantity before saving.</p>
              <p>These numbers are an estimate, not verified data.</p>
            </div>
          }
        />
      )}
    </div>
  )
}

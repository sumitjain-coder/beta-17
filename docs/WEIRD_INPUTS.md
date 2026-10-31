# Weird-input pass (plan section 9)

Run each case once by hand before the demo. "Expected" is what the code I read should do. Fill the last two columns with what you actually saw. If the result differs from "Expected", it is a bug: fix it or write down the honest answer.

| # | Case | How to trigger | Expected | Actual | Pass |
|---|---|---|---|---|---|
| 1 | Strange unit in audit | Audit has no free-text unit. Use `POST /audit/submit` in `/docs` with `"unit": "handful"` | 422 with a clear message. No stock changes (all conversions happen before any write). | | |
| 2 | Unit with no conversion for that ingredient | Stock page: add an item in katori or cup where no conversion exists | The backend's error message shows in the form. Nothing is saved. | | |
| 3 | Same item in kg then g | Stock page: add rice 1 kg, then rice 500 g | One row, 1.5 kg. | | |
| 4 | Same item, two spellings | Stock page: add "arhar dal" when "toor dal" exists | Merges into the toor dal row through the alias. | | |
| 5 | Recipe with an ingredient not in the table | Recipes page: add a recipe with "dragon fruit powder" | A clear message naming the ingredient. **Read the note below: this may be a 500.** | | |
| 6 | Dish with no recipe, AI unreachable | Unset the LLM key, estimate a dish | "Unavailable, enter ingredients manually". No invented numbers. | | |
| 7 | AI returns junk | Use a fake provider or break the key | Validation error shown, nothing saved. | | |
| 8 | Mark done twice | Double-click, or press again after done | Second call returns `already_done`, shows "already marked done", no second deduction. | | |
| 9 | Stock short at deduction | Mark Dal Tadka done (toor dal short by 40 g) | Deducts 200 g, toor dal is 0, shortfall shown. Never negative. | | |
| 10 | Household size changed after planning | Change household size on a page that has it, then open the planner | Already planned meals keep their servings. The new size is only the default for new meals. Use **Change** to update one. | | |
| 11 | Audit with no stock | Empty the stock, open Audit | "No stock to check yet" message. | | |
| 12 | Audit with fewer than 5 items | Keep 2 items in stock | Shorter audit with a message saying how many. | | |
| 13 | Audit with a large gap | Enter 20% of the expected amount for one item | Shown as off by about 80%, stock is corrected, "after" error is 0. | | |
| 14 | Shopping list with no plan | New week with nothing planned, press Build list | "Nothing is missing" message. No error. | | |
| 15 | Shopping refresh keeps ticks | Tick an item, change the plan, refresh | Ticked item stays ticked. No duplicate rows. | | |
| 16 | Backend stops mid-demo | Stop uvicorn while the app is open, click around | Banner / error boxes with a clear message. No blank page. | | |
| 17 | Backend comes back | Restart uvicorn, press "Try again" | Page recovers without a full reload. | | |
| 18 | Changing a finished meal | Planner: look at a done meal | No Change button (changing it would reset it to planned). | | |

## Notes from reading the code

**Case 5 may be a bug (Role 2's `routers/recipes.py`).** In `create_recipe`, `find_ingredient()` returns `None` for an unknown name, and the next line uses `ingredient.id`. That would be an unhandled `AttributeError` and a 500 error. The AI-draft save path (`/recipes/estimate/save`) handles this properly and returns 422 with the list of missing ingredients. `create_recipe` needs the same check. If it is a 500, the "offer to create the ingredient" answer from the plan does not exist yet, so either add it or tell judges honestly what happens.

**Case 18 is protected only in the frontend.** `PUT /plan/{date}/{meal_type}` in `routers/planner.py` sets `status = "planned"` even when the meal was done. Anyone calling the API directly could un-finish a meal and then deduct stock again. Ask Role 2 to return 409 when the existing meal is done.

**Case 10 is a deliberate choice, say it out loud.** Household size is a number in the browser and is only a default. We do not silently rescale meals already planned, because that would change a shopping list the family may already have acted on.

**Duplicate recipe names.** `GET /suggestions` attaches `recipe_id` by recipe name. Two recipes with the same name would get the wrong id. `/recipes/estimate/save` blocks duplicate names, but `POST /recipes` does not.

## Result summary (fill in after the run)

- Date and time of the run:
- Run by:
- Cases passed: __ / 18
- Bugs found and who owns them:
- Anything we will tell judges honestly instead of fixing:

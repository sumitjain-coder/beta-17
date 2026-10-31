# KitchenSync

A household web app that links three things that are usually separate: the **meal plan**, the **recipes** and the **kitchen stock**.

Plan the week, see what is available and what is missing, hand the shopping list to a quick-commerce app, cook and press **Mark done** so stock drops automatically, then run a weekly **stock audit** to see how accurate the stock list really is.

**Golden rule:** code does all the maths (units, scaling, stock checks, deduction, scoring, audit). The LLM is optional, only drafts recipes for unknown dishes, and a human reviews every draft. With the LLM switched off, the whole app still works.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), Tailwind CSS, react-router |
| Backend | Python, FastAPI, Pydantic |
| Database | MySQL 8 (Docker), SQLAlchemy |
| Tests | pytest |
| Optional AI | One LLM provider class, chosen by environment variables |

## Setup (same on every laptop)

You need Docker, Python 3.10+ and Node 18+.

```bash
# 1. Clone and configure
git clone <repo-url> && cd <repo-folder>
cp .env.example .env            # Windows: copy .env.example .env

# 2. Database
docker compose up -d

# 3. Backend
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.reset_db          # rebuilds tables and loads seed data
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev                     # URL is printed by Vite
```

The frontend talks to `http://localhost:8000` by default. To point it elsewhere, set `VITE_API_URL` in `frontend/.env`.

**The schema is rebuilt, not migrated.** There is no Alembic. When someone changes the schema, everyone pulls and runs `python -m app.reset_db` again. This wipes local data and reloads the demo seed.

### Optional: AI recipe drafts

Set the LLM key and provider in `.env` (see `.env.example`). Without a key, the "estimate recipe" call returns a clear "unavailable, enter ingredients manually" message and the rest of the app is unaffected. The key lives only in `.env` on the server. It is never in the repo or the frontend.

### Run the tests

```bash
cd backend
pytest
```

Tests use an in-memory SQLite database, so Docker does not need to be running.

## Demo script (about 5 minutes)

`reset_db` loads a realistic demo kitchen: 31 recipes, 23 stock items, 12 planned meals over today and the next three days (4 servings), and two past audits. **The stock numbers and the past audits are seeded demo data, not real history. Say so.**

1. **Today.** Poha is ready to cook. Dal Tadka is short of toor dal (needs 240 g, has 200 g, short 40 g). Khichdi is short of peas by 60 g.
2. **Planner.** Open the week. Short meals are flagged. Change a meal, and look at the suggestions made from current stock (they show why: "you have 5 of 6 ingredients").
3. **Shopping.** Press *Build list from plan*. The week-level list sums needs across meals before comparing with stock (onion, oil, paneer, besan). Tick one item. Copy the text, show the WhatsApp link, open a quick-commerce search link.
4. **Mark done.** Go to Today and mark Poha done. Stock drops. Click again: the app says it was already done and deducts nothing.
5. **Short on stock.** Mark Dal Tadka done anyway. Toor dal goes to zero, the shortfall is recorded and shown. Nothing goes negative.
6. **Audit.** Enter real amounts for the five picked items (the pick includes atta and sugar, which drifted before). See matched count, average error before and after, and the drift ranking (sugar: "list too high").

## Hand-off to quick-commerce apps: what is and is not real

There is **no public ordering API** for Blinkit, Zepto, Instamart or BigBasket. The app does not place orders. It gives you a copyable list, a WhatsApp share link, and per-item links that open each app's search page. You add items to the cart and pay inside the app. The app says this on screen.

Those app URLs can change. They live in `QUICK_COMMERCE_APPS` in `backend/app/logic/handoff.py`, so fixing one is a one-line edit. Check them on a real phone before a demo.

## How it works (short)

- Everything is stored in **base units**: grams, millilitres or count. Household units (katori, cup, tbsp, pinch) are converted only when a person types or reads a quantity. Some conversions depend on the ingredient, and an unknown conversion raises an error instead of guessing.
- All tables point to one shared `ingredients` table (one canonical name, with aliases such as "arhar dal"), so recipes, stock and shopping are comparable.
- **Stock check:** for the week, needs are added up across all planned meals before comparing with stock.
- **Mark done:** one database transaction. If stock is short it deducts what exists, records the shortfall and tells the user. Marking twice does not deduct twice.
- **Shopping list:** built from the week's missing items. Refreshing keeps ticked items, updates quantities, and never duplicates a row. Meals before today are not shopped for.
- **Audit:** picks up to 5 items, scored `0.6 x past drift + 0.4 x staleness` (14 days since last change counts as maximum). A count matches if it is within 10% or within 10 g/ml (small amounts). Count items must match exactly. Stock is then corrected and the change is recorded in `stock_movements` with reason `audit`.

## Privacy

- We store only household size, stock and plans. No names, phone numbers or addresses.
- The household size is kept in the browser (`localStorage`) as a plain number.
- LLM calls send only a dish name and a serving count. Never stock or personal data.
- API keys live only in `.env` on the server. `.env` is in `.gitignore`.

## Known limits (honest list)

- No receipt or barcode scanning, live prices, IoT fridge, or multiple households or logins. See `docs/PITCH.md` for why each was cut.
- Audit history recalculates old summaries using the current tolerance, because the matched flag is not stored.
- Past audits and starting stock in the demo are seeded.

## Who owns what

| Area | Owner |
|---|---|
| Schema, units, stock check, mark done | Role 1 |
| Recipes, scaling, planner, suggestions, LLM | Role 2 |
| Frontend | Role 3 |
| Infra, shopping, hand-off, audit, demo seed, glue | Role 4 |

Only edit files you own. Ask the owner or open a small pull request for anything else. `main` must always run. After each good integration, tag it (`demo-ok-N`). Never commit `.env` or keys.

## Troubleshooting

| Problem | Fix |
|---|---|
| Frontend shows "Could not reach the server" | Backend is not running or `VITE_API_URL` is wrong. Open `http://localhost:8000/health`. |
| Backend cannot connect to the database | `docker compose ps`, wait for MySQL to be healthy, check `.env` matches `docker-compose.yml`. |
| Data looks wrong after a pull | Run `python -m app.reset_db` again. |
| Docker will not run on a laptop | Tell Role 4. Use a shared database hosted by one teammate, or a free hosted MySQL. |

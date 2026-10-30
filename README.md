# KitchenSync

Household meal plan + recipes + kitchen stock in one loop.
Golden rule: code does all the math; the LLM is optional and always reviewed by a human.

## Setup (same on every laptop)
1. Clone repo, then `cp .env.example .env`
2. Start DB: `docker compose up -d`
3. Backend:
   ```
   cd backend
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python -m app.reset_db        # after Role 1 pushes it
   uvicorn app.main:app --reload
   ```
   Open http://localhost:8000/docs
4. Frontend: `cd frontend && npm install && npm run dev`
5. Tests: `cd backend && pytest`

## Privacy
Only household size, stock and plans are stored. LLM calls send only a dish name and serving count.

## Note on ordering
There are no public quick-commerce ordering APIs. We hand off via a copyable list, WhatsApp link and search deep links.

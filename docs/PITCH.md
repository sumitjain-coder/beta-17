# KitchenSync pitch notes

Judges care about decisions and defence, not polish. Keep slides plain. Any member can be asked anything.

## 1. The user (fill in from the real conversation)

Section 2 of the judging criteria asks whether you spoke to a real person. Do not invent this. Spend 15 minutes with someone who actually cooks for a household (a parent or a flatmate), then fill in the table with their words.

**Who:** (role in the household, how many people they cook for. No name needed.)
**Date:**

| What they said (their words) | What we changed because of it |
|---|---|
| | |
| | |
| | |

Questions worth asking:
- When do you find out something is missing: when you plan, when you shop, or when you start cooking?
- How do you keep track of what is in the kitchen today?
- What do you do when you buy something and don't note it down?
- Would you press "Mark done" after every meal? What would make you forget?
- Would you check five items once a week? How long would you give it?

The last two answers matter most. If they say they would forget to press Mark done, that is exactly the case the audit and its "list too high" label exist for. Say so.

## 2. The one-line story

Three things that are normally separate (what to cook, what we have, what to buy) are one loop here. For each planned meal the app scales the recipe to the household, checks it against live stock, builds the shopping list, and deducts what was used. The audit then measures how wrong the stock list has become.

## 3. "What we deliberately did not build" slide

| Cut | Why we cut it | What we do instead |
|---|---|---|
| Receipt and barcode scanning | Needs a vision model we cannot depend on, and we cannot show its accuracy honestly. | Manual entry plus the weekly audit, which measures how out of date stock is. |
| Live quick-commerce ordering and price comparison | No public ordering API, and no way to verify that a price is current. | A copyable list, a WhatsApp link and per-item search links. We say on screen that this is not ordering. |
| Smart fridge / IoT | We have no device, so we could not demo it honestly. | Nothing. The audit is the manual check. |
| Multi-household roles and logins | One household keeps the loop simple and stable, and avoids storing personal data. | One shared household, no accounts. |
| AI-generated quantities as the default | A wrong gram figure silently breaks stock maths. | Numbers come from our curated library. The LLM only drafts for unknown dishes and a human edits and saves. |

Each member must be able to say why each of these was cut. The common answer: stability and honesty over breadth, since judges score a working core flow above size.

## 4. Two-minute explanation for each role

Each person also needs one worked example with real numbers, and their own tests ready to run.

**Role 4 (shopping, audit, glue): example numbers**
- *Shopping:* Dal Tadka for 4 needs 240 g toor dal. Stock has 200 g. Missing 40 g, so the list shows 40 g. Two meals that both need onion are added together first, then compared with stock once, so stock is not counted twice.
- *Rounding:* the list rounds up to a whole g, ml or piece, so we never tell someone to buy less than is missing.
- *Audit match:* expected 300 g, real 280 g. Error is 20 / 300 = 6.7%, inside the 10% tolerance, so it matches. Expected 500 g, real 350 g is 30% off, so it does not. Small amounts match within 10 g/ml. Count items must match exactly.
- *Audit pick:* score is 0.6 x past drift + 0.4 x staleness. Items never audited assume drift 0.3. Zero-stock items are skipped.
- *Why trust the audit:* expected is read from stock at the moment of submit, not taken from the browser. Every unit conversion happens before any write, so a bad unit changes nothing.

**Run your tests live:** `cd backend && pytest`. Mine are `test_shopping.py`, `test_handoff.py`, `test_shopping_router.py`, `test_audit_logic.py`, `test_audit_router.py`, `test_demo_seed.py`.

## 5. "What happens if...?" answers for Role 4's parts

| Question | Honest answer |
|---|---|
| ...you tap a Blinkit link and it breaks? | Third-party URLs can change. They are in one list in `handoff.py`, a one-line fix. We tested them on a real phone, and the app already says it is a search hand-off. |
| ...I refresh the list after ticking items? | Ticked items stay ticked, quantities update, and nothing is duplicated. |
| ...there is nothing missing? | The list is empty and the app says nothing needs buying. |
| ...there are fewer than 5 items in stock? | A shorter audit, with a message saying so. |
| ...there is no stock at all? | "No stock to check yet". No audit runs. |
| ...I type a unit like "a handful"? | The server returns a clear error and nothing changes. We never guess. |
| ...the audit finds a big gap? | It shows the gap, corrects stock to the real number, records it as an `audit` movement, and the drift ranking shows which ingredient keeps drifting and in which direction. |
| ...an old audit is shown after you change the tolerance? | History is recomputed with the current tolerance, because we do not store the matched flag. We know this limitation. |
| ...the demo numbers look too good? | The starting stock and two past audits are seeded demo data. We say so. |

## 6. Honest statements to say out loud

- The hand-off is search links, not ordering.
- The demo kitchen and the two past audits are seeded.
- Household size is a browser setting, not stored on the server.
- The LLM is optional. The app works with it switched off.

## 7. Git and tags (Role 4)

```bash
git tag demo-ok-3     # audit working end to end
git tag demofinal     # after the weird-input pass, README final, pitch rehearsed
git push origin --tags
```

Check commit history every few hours. The organisers require one commit every 6 hours, and our own rule is 3. If someone has gone 4 hours without a commit, ping the team.

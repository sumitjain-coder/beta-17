"""Shopping hand-off (owner: Role 4). Pure functions, no database, no LLM.

There is NO public ordering API for quick-commerce apps. So we hand off by:
  1. a copyable text list,
  2. a WhatsApp share link,
  3. per-item links that open each app's SEARCH page (user adds to cart there).

URL formats of third-party apps can change. They live in QUICK_COMMERCE_APPS
below, so fixing one is a one-line edit. TEST ON A REAL PHONE before the demo.
"""
from datetime import date
from decimal import Decimal as D, ROUND_CEILING
from urllib.parse import quote

from app.logic.units import friendly

QUICK_COMMERCE_APPS = [
    {"key": "blinkit", "name": "Blinkit",
     "search_url": "https://blinkit.com/s/?q={q}"},
    {"key": "zepto", "name": "Zepto",
     "search_url": "https://www.zeptonow.com/search?query={q}"},
    {"key": "instamart", "name": "Swiggy Instamart",
     "search_url": "https://www.swiggy.com/instamart/search?custom_back=true&query={q}"},
    {"key": "bigbasket", "name": "BigBasket",
     "search_url": "https://www.bigbasket.com/ps/?q={q}"},
]

NOTE = ("There is no public ordering API for quick-commerce apps. These links open "
        "each app's search page; you add items to the cart and pay inside the app.")


def format_quantity(quantity, base_unit: str) -> str:
    """Display text for a quantity to BUY. Rounded UP to a whole g / ml / piece,
    so we never tell the user to buy less than is missing.
    1500 g -> '1.5 kg', 2.4 count -> '3'."""
    q = D(str(quantity)).to_integral_value(rounding=ROUND_CEILING)
    if base_unit == "count":
        return f"{q:f}"
    return friendly(q, base_unit)


def build_text(items: list, week_start: date) -> str:
    title = f"KitchenSync shopping list (week of {week_start.day} {week_start.strftime('%b %Y')})"
    lines = [f"- {i['name'].capitalize()}: {format_quantity(i['quantity'], i['unit'])}"
             for i in items]
    return "\n".join([title] + lines)


def whatsapp_link(text: str) -> str:
    return "https://wa.me/?text=" + quote(text, safe="")


def search_links(name: str) -> dict:
    q = quote(name, safe="")
    return {app["key"]: app["search_url"].format(q=q) for app in QUICK_COMMERCE_APPS}


def build_handoff(items: list, week_start: date) -> dict:
    """items = rows from shopping.list_shopping(). Ticked items are already
    bought, so they are left out of the hand-off."""
    todo = [i for i in items if not i["checked"]]
    if not todo:
        return {"week_start": week_start, "count": 0, "text": "", "whatsapp_link": None,
                "apps": [{"key": a["key"], "name": a["name"]} for a in QUICK_COMMERCE_APPS],
                "items": [], "note": NOTE, "message": "Nothing left to buy."}
    text = build_text(todo, week_start)
    return {
        "week_start": week_start,
        "count": len(todo),
        "text": text,
        "whatsapp_link": whatsapp_link(text),
        "apps": [{"key": a["key"], "name": a["name"]} for a in QUICK_COMMERCE_APPS],
        "items": [{"id": i["id"], "name": i["name"],
                   "quantity_text": format_quantity(i["quantity"], i["unit"]),
                   "links": search_links(i["name"])} for i in todo],
        "note": NOTE,
        "message": None,
    }

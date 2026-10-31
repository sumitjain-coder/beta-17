from datetime import date
from decimal import Decimal as D
from app.models import MealPlan, StockItem, StockMovement
from app.logic import stock
from app.logic.units import to_base


def _meal(db, recipe_id, servings, mtype, day=None):
    m = MealPlan(date=day or date.today(), meal_type=mtype,
                 recipe_id=recipe_id, servings=servings)
    db.add(m)
    db.commit()
    return m


def test_merge_kg_and_g_into_one_row(db):
    stock.add_stock(db, 1, to_base(1, "kg", "toor dal", "g"))
    stock.add_stock(db, 1, to_base(500, "g", "toor dal", "g"))
    rows = db.query(StockItem).all()
    assert len(rows) == 1 and rows[0].quantity == D(1500)


def test_check_meal_reports_missing(db):          # 5 people x 90 g = 450 g
    stock.add_stock(db, 1, D(400))
    m = _meal(db, 1, 5, "lunch")
    row = stock.check_meal(db, m.id)[0]
    assert (row["needed"], row["available"], row["missing"]) == (D(450), D(400), D(50))


def test_week_aggregates_across_meals(db):        # two meals need 200 g onion each
    stock.add_stock(db, 2, D(300))
    _meal(db, 2, 1, "lunch")
    _meal(db, 2, 1, "dinner")
    res = stock.check_scope(db, "week")
    assert res["summary"][0]["missing"] == D(100)          # 400 needed, 300 in stock
    assert [m["ok"] for m in res["meals"]] == [True, False]


def test_double_done_deducts_once(db):
    stock.add_stock(db, 1, D(1000))
    m = _meal(db, 1, 5, "lunch")
    stock.mark_done(db, m.id)
    second = stock.mark_done(db, m.id)
    assert second["already_done"] is True
    assert db.query(StockItem).one().quantity == D(550)
    assert db.query(StockMovement).filter_by(reason="meal_done").count() == 1


def test_done_with_short_stock_never_negative(db):
    stock.add_stock(db, 1, D(100))
    m = _meal(db, 1, 5, "lunch")                  # needs 450
    res = stock.mark_done(db, m.id)
    assert db.query(StockItem).one().quantity == D(0)
    assert res["shortfalls"][0]["short_by"] == D(350)

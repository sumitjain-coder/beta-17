"""Pure tests for logic/audit.py - no database."""
from decimal import Decimal as D

from app.logic import audit


def test_tolerance_relative_for_big_amounts():
    assert audit.is_match(400, 380, "g")        # 5% off, tolerance 40
    assert not audit.is_match(400, 350, "g")    # 12.5% off


def test_tolerance_absolute_floor_for_small_amounts():
    assert audit.is_match(50, 58, "g")          # tolerance max(5, 10) = 10
    assert not audit.is_match(50, 61, "g")


def test_counts_must_match_exactly():
    assert audit.is_match(5, 5, "count")
    assert not audit.is_match(5, 4, "count")


def test_pct_error_cases():
    assert audit.pct_error(400, 380) == D("0.05")
    assert audit.pct_error(100, 500) == D(1)    # capped at 100%
    assert audit.pct_error(0, 0) == D(0)
    assert audit.pct_error(0, 200) == D(1)


def test_evaluate_numbers():
    rows = [
        {"ingredient_id": 1, "name": "toor dal", "unit": "g", "expected": 400, "actual": 380},
        {"ingredient_id": 2, "name": "onion", "unit": "count", "expected": 5, "actual": 3},
        {"ingredient_id": 3, "name": "sugar", "unit": "g", "expected": 0, "actual": 200},
    ]
    ev = audit.evaluate(rows)
    assert ev["total"] == 3 and ev["matched"] == 1
    assert round(float(ev["accuracy"]), 4) == 0.3333
    assert round(float(ev["avg_error_before"]), 4) == 0.4833   # (0.05 + 0.4 + 1) / 3
    assert ev["avg_error_after"] == 0
    assert ev["items"][1]["gap"] == D(-2)


def test_evaluate_empty():
    ev = audit.evaluate([])
    assert ev["total"] == 0 and ev["accuracy"] is None


def test_score_prefers_drifted_and_stale_items():
    assert audit.score_item(D("0.8"), 0) > audit.score_item(D("0.0"), 0)
    assert audit.score_item(None, 14) > audit.score_item(None, 1)
    assert audit.score_item(None, 100) == audit.score_item(None, 14)   # staleness capped


def test_rank_for_pick_order_limit_and_reason():
    cands = [
        {"ingredient_id": 1, "name": "rice", "unit": "g", "expected": 1, "avg_drift": None, "days_since_change": 1},
        {"ingredient_id": 2, "name": "sugar", "unit": "g", "expected": 1, "avg_drift": D("0.8"), "days_since_change": 2},
        {"ingredient_id": 3, "name": "salt", "unit": "g", "expected": 1, "avg_drift": None, "days_since_change": 20},
    ]
    # salt: 0.6*0.3 + 0.4*1.0 = 0.58 ; sugar: 0.6*0.8 + 0.4*(2/14) = 0.537 ; rice ~0.21
    top = audit.rank_for_pick(cands, 2)
    assert [c["name"] for c in top] == ["salt", "sugar"]
    assert "not changed for 20 days" in top[0]["reason"]
    assert "off by 80%" in top[1]["reason"]


def test_rank_ties_are_stable_by_name():
    c = lambda i, n: {"ingredient_id": i, "name": n, "unit": "g", "expected": 1,
                      "avg_drift": None, "days_since_change": 3}
    assert [x["name"] for x in audit.rank_for_pick([c(2, "b"), c(1, "a")])] == ["a", "b"]


def test_pick_reason_fallback():
    assert audit.pick_reason(D("0.02"), 1) == "routine check"


def test_drift_ranking_and_direction():
    rows = [
        {"ingredient_id": 1, "name": "sugar", "unit": "g", "expected": 500, "actual": 100},  # 80% too high
        {"ingredient_id": 1, "name": "sugar", "unit": "g", "expected": 300, "actual": 270},  # 10%
        {"ingredient_id": 2, "name": "rice", "unit": "g", "expected": 1000, "actual": 1050},  # 5%, too low
    ]
    rank = audit.drift_ranking(rows)
    assert [r["name"] for r in rank] == ["sugar", "rice"]
    assert rank[0]["audits"] == 2 and round(float(rank[0]["avg_error"]), 2) == 0.45
    assert rank[0]["direction"] == "list too high"
    assert rank[1]["direction"] == "list too low"

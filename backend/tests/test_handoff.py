"""Pure tests for logic/handoff.py - no database needed."""
from datetime import date
from decimal import Decimal as D
from urllib.parse import unquote

from app.logic import handoff

WK = date(2026, 11, 2)


def _item(id, name, qty, unit, checked=False):
    return {"id": id, "name": name, "quantity": D(str(qty)), "unit": unit, "checked": checked}


def test_format_quantity():
    assert handoff.format_quantity(D(50), "g") == "50 g"
    assert handoff.format_quantity(D(1500), "g") == "1.5 kg"
    assert handoff.format_quantity(D("333.333"), "g") == "334 g"      # rounded UP
    assert handoff.format_quantity(D("2.4"), "count") == "3"
    assert handoff.format_quantity(D(3), "count") == "3"
    assert handoff.format_quantity(D(2000), "ml") == "2 L"


def test_text_lists_items():
    text = handoff.build_text([_item(1, "toor dal", 50, "g"), _item(2, "onion", 3, "count")], WK)
    assert "week of 2 Nov 2026" in text
    assert "- Toor dal: 50 g" in text
    assert "- Onion: 3" in text


def test_whatsapp_link_is_encoded_and_round_trips():
    text = "Toor dal & rice: 50 g\nOnion: 3"
    link = handoff.whatsapp_link(text)
    assert link.startswith("https://wa.me/?text=")
    assert " " not in link and "\n" not in link and "&" not in link.split("text=")[1]
    assert unquote(link.split("text=")[1]) == text


def test_search_links_cover_all_apps_and_encode_name():
    links = handoff.search_links("toor dal & co")
    assert set(links) == {a["key"] for a in handoff.QUICK_COMMERCE_APPS}
    for url in links.values():
        assert url.startswith("https://")
        assert "toor%20dal%20%26%20co" in url


def test_handoff_skips_ticked_items():
    out = handoff.build_handoff([_item(1, "toor dal", 50, "g"),
                                 _item(2, "onion", 3, "count", checked=True)], WK)
    assert out["count"] == 1
    assert [i["name"] for i in out["items"]] == ["toor dal"]
    assert "Onion" not in out["text"]


def test_handoff_empty_list():
    out = handoff.build_handoff([], WK)
    assert out["count"] == 0 and out["whatsapp_link"] is None and out["items"] == []
    assert out["message"] == "Nothing left to buy."


def test_handoff_all_ticked_is_empty():
    out = handoff.build_handoff([_item(1, "onion", 3, "count", checked=True)], WK)
    assert out["count"] == 0


def test_handoff_always_states_no_public_api():
    assert "no public ordering api" in handoff.build_handoff([], WK)["note"].lower()

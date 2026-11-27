"""Тести логіки: python -m pytest -v"""
import pytest

import logic
from models import Battle

B1 = Battle("2026-11-20", "F/A-18C", "РБ", "перемога", 4, 12)
B2 = Battle("2026-11-21", "F/A-18C", "РБ", "поразка", 1, 8)
B3 = Battle("2026-11-21", "Leopard 2A4", "АБ", "перемога", 6, 10)
ALL = [B1, B2, B3]


def test_make_record_normalizes_and_converts():
    b = logic.make_record("2026-11-23", " F/A-18C ", "рб", "Перемога", "3", "9.5")
    assert isinstance(b, Battle)
    assert (b.vehicle, b.mode, b.result) == ("F/A-18C", "РБ", "перемога")
    assert b.kills == 3 and b.minutes == 9.5


@pytest.mark.parametrize("args", [
    ("23.11.2026", "F/A-18C", "РБ", "перемога", 3, 9),     # дата не ISO
    ("2026-11-23", "F/A-18C", "РБ", "перемога", "три", 9),  # текст замість числа
    ("2026-11-23", "F/A-18C", "РБ", "перемога", -1, 9),     # від'ємне
    ("2026-11-23", "F/A-18C", "ХЗ", "перемога", 3, 9),      # невідомий режим
    ("2026-11-23", "", "РБ", "перемога", 3, 9),             # порожня техніка
    ("2026-11-23", "F/A-18C", "РБ", "нічия", 3, 9),         # невідомий результат
])
def test_make_record_rejects_bad_input(args):
    with pytest.raises(ValueError):
        logic.make_record(*args)


def test_find_by_vehicle_ignores_case():
    assert logic.find_by_vehicle(ALL, "f/a-18c") == [B1, B2]
    assert logic.find_by_vehicle(ALL, "МіГ-29") == []


def test_win_rate_by_vehicle():
    assert logic.win_rate_by_vehicle(ALL) == {"F/A-18C": 50.0, "Leopard 2A4": 100.0}
    assert logic.win_rate_by_vehicle([]) == {}


def test_average_kills():
    assert logic.average_kills(ALL) == round(11 / 3, 2)
    assert logic.average_kills([]) == 0


def test_best_battle():
    assert logic.best_battle(ALL) == B3
    assert logic.best_battle([]) is None


def test_kills_by_mode():
    assert logic.kills_by_mode(ALL) == {"РБ": 5, "АБ": 6}


def test_battle_to_dict_and_is_win():
    d = B1.to_dict()
    assert d["vehicle"] == "F/A-18C" and d["kills"] == 4 and d["id"] is None
    assert B1.is_win() and not B2.is_win()


# ---- довідник техніки ----
import catalog


def test_catalog_finds_leopards_with_br():
    found = catalog.search("leopard 2a5")
    names = [v["name"] for v in found]
    assert "Leopard 2A5" in names
    v = next(v for v in found if v["name"] == "Leopard 2A5")
    assert set(v["br"]) == {"АБ", "РБ", "СБ"} and v["br"]["РБ"] > 10
    assert v["nation"] and v["type"]


def test_catalog_ignores_case_spaces_and_short_queries():
    assert catalog.search("LEOPARD2A5") == catalog.search("leopard 2a5")
    assert catalog.search("l") == []
    assert catalog.search("zzzzzz") == []
    assert len(catalog.search("leopard", limit=5)) == 5

"""Перевірки функцій з logic.py і storage.py. Запуск: python tests.py"""

import os
import logic
import storage

B1 = {"date": "2026-11-20", "vehicle": "F/A-18C", "mode": "РБ",
      "result": "перемога", "kills": 4, "minutes": 12.0}
B2 = {"date": "2026-11-21", "vehicle": "F/A-18C", "mode": "РБ",
      "result": "поразка", "kills": 1, "minutes": 8.0}
B3 = {"date": "2026-11-21", "vehicle": "Leopard 2A4", "mode": "АБ",
      "result": "перемога", "kills": 6, "minutes": 10.0}
ALL = [B1, B2, B3]


def expect_error(func, *args):
    try:
        func(*args)
    except ValueError:
        return True
    return False


# make_record
r = logic.make_record("2026-11-23", "F/A-18C", "рб", "Перемога", "3", "9.5")
assert r["mode"] == "РБ" and r["result"] == "перемога"
assert r["kills"] == 3 and r["minutes"] == 9.5
assert expect_error(logic.make_record, "23.11.2026", "F/A-18C", "РБ", "перемога", 3, 9)
assert expect_error(logic.make_record, "2026-11-23", "F/A-18C", "РБ", "перемога", "три", 9)
assert expect_error(logic.make_record, "2026-11-23", "F/A-18C", "РБ", "перемога", -1, 9)
assert expect_error(logic.make_record, "2026-11-23", "F/A-18C", "ХЗ", "перемога", 3, 9)
assert expect_error(logic.make_record, "2026-11-23", "", "РБ", "перемога", 3, 9)

# find_by_vehicle
assert len(logic.find_by_vehicle(ALL, "F/A-18C")) == 2
assert len(logic.find_by_vehicle(ALL, "f/a-18c")) == 2
assert logic.find_by_vehicle(ALL, "МіГ-29") == []

# win_rate_by_vehicle
rates = logic.win_rate_by_vehicle(ALL)
assert rates["F/A-18C"] == 50.0
assert rates["Leopard 2A4"] == 100.0
assert logic.win_rate_by_vehicle([]) == {}

# average_kills
assert logic.average_kills(ALL) == round(11 / 3, 2)
assert logic.average_kills([]) == 0

# best_battle
assert logic.best_battle(ALL) == B3
assert logic.best_battle([]) is None

# storage: збереження, читання і пошкоджений рядок
TEST_FILE = "test_data.txt"
storage.save(TEST_FILE, ALL)
with open(TEST_FILE, "a", encoding="utf-8") as f:
    f.write("сміття;без;потрібних;полів\n")
    f.write("2026-11-22;Т-80;РБ;поразка;два;7\n")
loaded, bad = storage.load(TEST_FILE)
os.remove(TEST_FILE)
assert loaded == ALL
assert len(bad) == 2
assert storage.load("немає_такого_файла.txt") == ([], [])

print("усі перевірки пройдено")

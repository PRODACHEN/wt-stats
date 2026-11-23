"""Перевірки logic.py, storage.py і app.py. Запуск: python tests.py
Тести працюють з окремою базою test_data.db і не чіпають ваші дані."""

import os
import logic
import storage

storage.DB = "test_data.db"
if os.path.exists(storage.DB):
    os.remove(storage.DB)

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


# ---- logic.py ----
r = logic.make_record("2026-11-23", "F/A-18C", "рб", "Перемога", "3", "9.5")
assert r["mode"] == "РБ" and r["result"] == "перемога"
assert r["kills"] == 3 and r["minutes"] == 9.5
assert expect_error(logic.make_record, "23.11.2026", "F/A-18C", "РБ", "перемога", 3, 9)
assert expect_error(logic.make_record, "2026-11-23", "F/A-18C", "РБ", "перемога", "три", 9)
assert expect_error(logic.make_record, "2026-11-23", "F/A-18C", "РБ", "перемога", -1, 9)
assert expect_error(logic.make_record, "2026-11-23", "F/A-18C", "ХЗ", "перемога", 3, 9)
assert expect_error(logic.make_record, "2026-11-23", "", "РБ", "перемога", 3, 9)

assert len(logic.find_by_vehicle(ALL, "f/a-18c")) == 2
assert logic.find_by_vehicle(ALL, "МіГ-29") == []

rates = logic.win_rate_by_vehicle(ALL)
assert rates["F/A-18C"] == 50.0 and rates["Leopard 2A4"] == 100.0
assert logic.win_rate_by_vehicle([]) == {}

assert logic.average_kills(ALL) == round(11 / 3, 2)
assert logic.average_kills([]) == 0

assert logic.best_battle(ALL) == B3
assert logic.best_battle([]) is None

# ---- storage.py (SQLite) ----
storage.init()
ids = [storage.add(b) for b in ALL]
assert len(storage.load()) == 3
assert len(storage.load("f/a-18c")) == 2
assert storage.delete(ids[0]) is True
assert storage.delete(ids[0]) is False          # вдруге вже немає
assert len(storage.load()) == 2
# спроба SQL-ін'єкції нічого не ламає
assert storage.load("'; DROP TABLE battles; --") == []
assert len(storage.load()) == 2

# ---- app.py (через тестовий клієнт Flask, без запуску сервера) ----
import app as webapp
client = webapp.app.test_client()

assert client.get("/battles").status_code == 200
ok = client.post("/battles", json={"date": "2026-11-23", "vehicle": "F/A-18C",
                                   "mode": "РБ", "result": "перемога",
                                   "kills": 5, "minutes": 11})
assert ok.status_code == 201
new_id = ok.get_json()["id"]
assert client.post("/battles").status_code == 400                       # без тіла
assert client.post("/battles", json={"date": "2026-11-23"}).status_code == 400
assert client.post("/battles", json={"date": "2026-11-23", "vehicle": "X",
                                     "mode": "РБ", "result": "перемога",
                                     "kills": "багато", "minutes": 5}).status_code == 400
assert client.post("/battles", json=[1, 2]).status_code == 400
assert len(client.get("/battles?vehicle=F/A-18C").get_json()) == 2
assert client.get("/report").get_json()["battles"] == 3
assert client.delete(f"/battles/{new_id}").status_code == 200
assert client.delete("/battles/99999").status_code == 404
assert client.get("/nema").status_code == 404

os.remove(storage.DB)
print("усі перевірки пройдено")

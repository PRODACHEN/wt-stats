"""Тести маршрутів Flask без запуску сервера, кожен на своїй порожній базі."""
import os
import sqlite3

import pytest

T = {"X-Admin-Token": "test-token"}
GOOD = {"date": "2026-11-23", "vehicle": "F/A-18C", "mode": "РБ",
        "result": "перемога", "kills": 5, "minutes": 11}


@pytest.fixture
def client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test.db")   # порожня база на кожен тест
    import app
    app.storage.init()
    app.app.config["TESTING"] = True
    return app.app.test_client()


def add(client, **changes):
    return client.post("/battles", json={**GOOD, **changes})


def test_add_and_list(client):
    r = add(client)
    assert r.status_code == 201
    battles = client.get("/battles").get_json()
    assert len(battles) == 1 and battles[0]["vehicle"] == "F/A-18C"


def test_filter_by_vehicle(client):
    add(client)
    add(client, vehicle="Leopard 2A4")
    assert len(client.get("/battles?vehicle=f/a-18c").get_json()) == 1


def test_add_rejects_text_kills(client):
    assert add(client, kills="багато").status_code == 400


def test_add_rejects_missing_field_and_empty_body(client):
    assert client.post("/battles", json={"date": "2026-11-23"}).status_code == 400
    assert client.post("/battles").status_code == 400
    assert client.post("/battles", json=[1, 2]).status_code == 400


def test_delete_missing_returns_404(client):
    assert client.delete("/battles/999").status_code == 404


def test_delete_existing(client):
    new_id = add(client).get_json()["id"]
    assert client.delete(f"/battles/{new_id}").status_code == 200
    assert client.get("/battles").get_json() == []


def test_report(client):
    add(client, kills=2)
    add(client, kills=6, result="поразка")
    r = client.get("/report").get_json()
    assert r["battles"] == 2 and r["average_kills"] == 4.0
    assert r["best_battle"]["kills"] == 6
    assert r["win_rate_by_vehicle"] == {"F/A-18C": 50.0}


def test_vehicle_report_uses_join(client):
    add(client)
    add(client, result="поразка")
    add(client, vehicle="Leopard 2A4", date="2026-10-05")
    rows = client.get("/report/vehicles").get_json()
    assert rows[0] == {"vehicle": "F/A-18C", "battles": 2, "wins": 1,
                       "win_rate": 50.0, "average_kills": 5.0}
    november = client.get("/report/vehicles?month=2026-11").get_json()
    assert [r["vehicle"] for r in november] == ["F/A-18C"]
    assert client.get("/report/vehicles?month=листопад").status_code == 400


def test_same_vehicle_stored_once(client):
    add(client)
    add(client, vehicle="f/a-18c")                       # інший регістр, та сама техніка
    conn = sqlite3.connect(os.environ["DB_PATH"])
    assert conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == 1
    conn.close()


def test_audit_log_records_add_and_delete(client):
    new_id = add(client).get_json()["id"]
    client.delete(f"/battles/{new_id}")
    assert client.get("/admin/log").status_code == 403    # без токена
    log = client.get("/admin/log?limit=10", headers=T).get_json()
    assert [row["action"] for row in log] == ["delete", "add"]
    assert all(row["battle_id"] == new_id and row["ts"] for row in log)


def test_admin_requires_token_and_hides_from_cloudflare(client):
    assert client.get("/admin/export").status_code == 403
    assert client.get("/admin/export", headers={**T, "CF-Connecting-IP": "1.2.3.4"}).status_code == 404
    assert client.get("/admin/export", headers=T).status_code == 200


def test_admin_import_and_delete_all(client):
    assert client.post("/admin/import", headers=T, json={"a": 1}).status_code == 400
    r = client.post("/admin/import", headers=T, json=[GOOD, {**GOOD, "vehicle": "Т-80У"}])
    assert r.status_code == 201 and r.get_json()["imported"] == 2
    assert client.delete("/admin/battles", headers=T).get_json()["deleted"] == 2


def test_unknown_route(client):
    assert client.get("/nema").status_code == 404

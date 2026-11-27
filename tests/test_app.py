"""Тести маршрутів Flask без запуску сервера, кожен на своїй порожній базі."""
import os
import sqlite3

import pytest

GOOD = {"date": "2026-11-23", "vehicle": "F/A-18C", "mode": "РБ",
        "result": "перемога", "kills": 5, "minutes": 11}
PASSWORD = "pass12345"


@pytest.fixture
def app_module(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test.db")   # порожня база на кожен тест
    import app
    app.storage.init()
    app.app.config["TESTING"] = True
    app.app.config["SESSION_COOKIE_SECURE"] = False      # тестовий клієнт ходить по http
    return app


def register(app_module, login="nikita"):
    """Новий клієнт (свій набір cookie) із зареєстрованим і залогіненим користувачем."""
    c = app_module.app.test_client()
    r = c.post("/register", json={"login": login, "password": PASSWORD})
    assert r.status_code == 201
    return c


@pytest.fixture
def client(app_module):
    return register(app_module)


def add(client, **changes):
    return client.post("/battles", json={**GOOD, **changes})


# ---- реєстрація і вхід ----

def test_register_validates_and_rejects_duplicate(app_module):
    c = app_module.app.test_client()
    assert c.post("/register", json={"login": "ab", "password": PASSWORD}).status_code == 400
    assert c.post("/register", json={"login": "abc", "password": "short"}).status_code == 400
    assert c.post("/register", json={"login": "abc", "password": PASSWORD}).status_code == 201
    other = app_module.app.test_client()
    assert other.post("/register", json={"login": "ABC", "password": PASSWORD}).status_code == 409


def test_password_stored_only_as_hash(client):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    h = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    conn.close()
    assert PASSWORD not in h and h.startswith(("scrypt:", "pbkdf2:"))


def test_login_logout_and_wrong_password(client, app_module):
    client.post("/logout")
    assert client.get("/battles").status_code == 401
    bad = client.post("/login", json={"login": "nikita", "password": "wrong-pass"})
    nobody = client.post("/login", json={"login": "nobody", "password": PASSWORD})
    assert bad.status_code == nobody.status_code == 401
    assert bad.get_json() == nobody.get_json()           # не підказуємо, чи існує логін
    ok = client.post("/login", json={"login": "nikita", "password": PASSWORD})
    assert ok.status_code == 200 and ok.get_json()["login"] == "nikita"
    assert client.get("/me").get_json()["is_admin"] is False


def test_no_session_gives_401(app_module):
    anon = app_module.app.test_client()
    assert anon.get("/battles").status_code == 401
    assert anon.post("/battles", json=GOOD).status_code == 401
    assert anon.get("/report").status_code == 401
    assert anon.get("/me").status_code == 401


# ---- бої ----

def test_add_and_list(client):
    assert add(client).status_code == 201
    battles = client.get("/battles").get_json()
    assert len(battles) == 1 and battles[0]["vehicle"] == "F/A-18C"


def test_add_rejects_bad_input(client):
    assert add(client, kills="багато").status_code == 400
    assert client.post("/battles", json={"date": "2026-11-23"}).status_code == 400
    assert client.post("/battles", json=[1, 2]).status_code == 400


def test_users_do_not_see_each_other(client, app_module):
    my_id = add(client).get_json()["id"]
    other = register(app_module, "vasya")
    add(other, vehicle="Т-80У")
    assert [b["vehicle"] for b in client.get("/battles").get_json()] == ["F/A-18C"]
    assert [b["vehicle"] for b in other.get("/battles").get_json()] == ["Т-80У"]
    assert other.get("/report").get_json()["battles"] == 1
    # чужий бій: 404, і він лишається на місці
    assert other.delete(f"/battles/{my_id}").status_code == 404
    assert len(client.get("/battles").get_json()) == 1
    assert client.delete(f"/battles/{my_id}").status_code == 200


def test_delete_missing_returns_404(client):
    assert client.delete("/battles/999").status_code == 404


def test_report_and_vehicle_report(client):
    add(client, kills=2)
    add(client, kills=6, result="поразка")
    add(client, vehicle="Leopard 2A4", date="2026-10-05")
    r = client.get("/report").get_json()
    assert r["battles"] == 3 and r["best_battle"]["kills"] == 6
    rows = client.get("/report/vehicles?month=2026-11").get_json()
    assert rows == [{"vehicle": "F/A-18C", "battles": 2, "wins": 1,
                     "win_rate": 50.0, "average_kills": 4.0}]
    assert client.get("/report/vehicles?month=листопад").status_code == 400


# ---- адмінка і журнал ----

def test_admin_only_for_admins_and_not_via_cloudflare(client, app_module):
    assert client.get("/admin/export").status_code == 403          # звичайний користувач
    app_module.storage.set_admin("nikita")
    assert client.get("/admin/export").status_code == 200
    assert client.get("/admin/export", headers={"CF-Connecting-IP": "1.2.3.4"}).status_code == 404
    assert app_module.app.test_client().get("/admin/log").status_code == 401   # без сесії


def test_admin_import_and_delete_all(client, app_module):
    app_module.storage.set_admin("nikita")
    assert client.post("/admin/import", json={"a": 1}).status_code == 400
    r = client.post("/admin/import", json=[GOOD, {**GOOD, "vehicle": "Т-80У"}])
    assert r.status_code == 201 and r.get_json()["imported"] == 2
    assert client.delete("/admin/battles").get_json()["deleted"] == 2


def test_audit_log_has_user(client, app_module):
    new_id = add(client).get_json()["id"]
    client.delete(f"/battles/{new_id}")
    app_module.storage.set_admin("nikita")
    log = client.get("/admin/log?limit=10").get_json()
    assert [row["action"] for row in log] == ["delete", "add", "register"]
    assert all(row["login"] == "nikita" and row["user_id"] for row in log)


def test_unknown_route(client):
    assert client.get("/nema").status_code == 404

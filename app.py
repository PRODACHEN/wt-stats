"""Вебсервіс статистики боїв. Запуск локально: python app.py
Далі у браузері: http://127.0.0.1:5000/battles (спершу /register або /login).
На сервері працює gunicorn (deploy/wt-stats.service)."""

import os
import sqlite3
from datetime import date

from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

import storage
import logic

load_dotenv()                          # читає .env з поточної теки (у git його немає)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]   # впаде при старті, якщо не задано: це добре
app.config["SESSION_COOKIE_SECURE"] = True            # cookie лише через HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True          # JavaScript не бачить cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Фронтенд живе на іншому домені, тому браузеру треба явно дозволити запити.
# Лише наш сайт, не "*". supports_credentials=True, щоб браузер надсилав cookie сесії
# (на фронтенді кожен fetch з credentials: "include").
# Для локальної перевірки фронтенду тимчасово додайте "http://localhost:8080".
CORS(app, origins=["https://prodachen.pp.ua"], supports_credentials=True)
app.json.ensure_ascii = False            # кирилиця в JSON як є, а не кодами \uXXXX
storage.init()

FIELDS = ("date", "vehicle", "mode", "result", "kills", "minutes")


# ---- користувачі і сесії ----

def current_user():
    """Повертає користувача поточної сесії або зупиняє запит з 401."""
    user_id = session.get("user_id")
    if user_id is None:
        abort(401)
    user = storage.get_user(user_id)
    if user is None:                     # користувача видалили, а cookie лишився
        session.clear()
        abort(401)
    return user


def require_admin():
    # Шар 2 з лаби 10: запит через Cloudflare (є CF-Connecting-IP) в адмінку не пускаємо.
    if "CF-Connecting-IP" in request.headers:
        abort(404)
    user = current_user()
    if not user["is_admin"]:
        abort(403)
    return user


def public(user):
    return {"id": user["id"], "login": user["login"], "is_admin": bool(user["is_admin"])}


@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    login = str(data.get("login", "")).strip()
    password = str(data.get("password", ""))
    if len(login) < 3 or len(login) > 30 or len(password) < 8:
        return jsonify({"error": "логін від 3 до 30 символів, пароль від 8"}), 400
    try:
        user_id = storage.add_user(login, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return jsonify({"error": "логін зайнятий"}), 409
    session.clear()
    session["user_id"] = user_id
    return jsonify(public(storage.get_user(user_id))), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    user = storage.get_user_by_login(str(data.get("login", "")).strip())
    # Одне повідомлення на обидва випадки: не підказуємо, які логіни існують.
    if user is None or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
        return jsonify({"error": "неправильний логін або пароль"}), 401
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(public(user))


@app.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/me")
def me():
    return jsonify(public(current_user()))


# ---- бої поточного користувача ----

@app.get("/battles")
def list_battles():
    user = current_user()
    vehicle = request.args.get("vehicle")        # ?vehicle=F/A-18C або None
    return jsonify([b.to_dict() for b in storage.load(user["id"], vehicle)])


@app.post("/battles")
def add_battle():
    user = current_user()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "очікується JSON-об'єкт"}), 400
    for field in FIELDS:
        if field not in data:
            return jsonify({"error": f"немає поля {field}"}), 400
    try:
        battle = logic.make_record(*(data[f] for f in FIELDS))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    new_id = storage.add(battle, user["id"])
    return jsonify({"id": new_id}), 201


@app.delete("/battles/<int:battle_id>")
def delete_battle(battle_id):
    user = current_user()
    # Чужий бій дає 404, а не 403: не підтверджуємо, що такий запис існує.
    if storage.delete(battle_id, user["id"]):
        return jsonify({"deleted": battle_id})
    return jsonify({"error": "бій не знайдено"}), 404


@app.get("/report")
def report():
    user = current_user()
    records = storage.load(user["id"])
    best = logic.best_battle(records)
    return jsonify({
        "battles": len(records),
        "average_kills": logic.average_kills(records),
        "win_rate_by_vehicle": logic.win_rate_by_vehicle(records),
        "kills_by_mode": logic.kills_by_mode(records),
        "best_battle": best.to_dict() if best else None,
    })


@app.get("/report/vehicles")
def report_vehicles():
    """Звіт через JOIN battles + vehicles. ?month=2026-11 (необов'язково)."""
    user = current_user()
    month = request.args.get("month")
    if month is not None:
        try:
            date.fromisoformat(month + "-01")
        except ValueError:
            return jsonify({"error": "month має бути у форматі РРРР-ММ"}), 400
    return jsonify(storage.vehicle_report(user["id"], month))


# ---- адміністративні маршрути (масові зміни даних) ----
# Захист у три шари:
#  1) nginx не пропускає /admin/ з інтернету взагалі (deploy/nginx.conf);
#  2) Flask відхиляє запит, що прийшов через Cloudflare (є CF-Connecting-IP);
#  3) Flask вимагає сесію користувача з is_admin = 1.
# Доступ до адмінки: з самого сервера (127.0.0.1:8000) або через Tailscale.

@app.get("/admin/export")
def admin_export():
    require_admin()
    return jsonify([b.to_dict() for b in storage.load(None)])


@app.get("/admin/log")
def admin_log():
    require_admin()
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "limit має бути числом"}), 400
    return jsonify(storage.load_log(max(1, min(limit, 500))))


@app.post("/admin/import")
def admin_import():
    admin = require_admin()
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "очікується JSON-масив боїв"}), 400
    records = []
    for i, item in enumerate(data):
        if not isinstance(item, dict) or any(f not in item for f in FIELDS):
            return jsonify({"error": f"запис {i}: бракує полів"}), 400
        try:
            records.append(logic.make_record(*(item[f] for f in FIELDS)))
        except ValueError as e:
            return jsonify({"error": f"запис {i}: {e}"}), 400
    for r in records:                    # спершу перевіряємо все, потім пишемо
        storage.add(r, admin["id"])      # імпортовані бої належать адміну
    return jsonify({"imported": len(records)}), 201


@app.delete("/admin/battles")
def admin_delete_all():
    admin = require_admin()
    return jsonify({"deleted": storage.delete_all(admin["id"])})


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "потрібно увійти"}), 401


@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "доступ заборонено"}), 403


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "такого маршруту немає"}), 404


@app.errorhandler(405)
def wrong_method(e):
    return jsonify({"error": "цей метод тут не підтримується"}), 405


if __name__ == "__main__":
    app.config["SESSION_COOKIE_SECURE"] = False   # локально без HTTPS
    app.run(debug=True)                  # лише локально; на сервері працює gunicorn

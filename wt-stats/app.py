"""Вебсервіс статистики боїв. Запуск: python app.py
Далі у браузері: http://127.0.0.1:5000/battles"""

import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import storage
import logic

load_dotenv()                          # читає .env з поточної теки (у git його немає)
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

app = Flask(__name__)

# Фронтенд живе на іншому домені, тому браузеру треба явно дозволити запити.
# Лише наш сайт, не "*": інакше будь-який сайт міг би ходити в API від імені відвідувача.
# Для локальної перевірки фронтенду тимчасово додайте "http://localhost:8080".
CORS(app, origins=["https://prodachen.pp.ua"])
app.json.ensure_ascii = False            # кирилиця в JSON як є, а не кодами \uXXXX
storage.init()

FIELDS = ("date", "vehicle", "mode", "result", "kills", "minutes")


@app.get("/battles")
def list_battles():
    vehicle = request.args.get("vehicle")        # ?vehicle=F/A-18C або None
    return jsonify(storage.load(vehicle))


@app.post("/battles")
def add_battle():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "очікується JSON-об'єкт"}), 400
    for field in FIELDS:
        if field not in data:
            return jsonify({"error": f"немає поля {field}"}), 400
    try:
        record = logic.make_record(*(data[f] for f in FIELDS))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    new_id = storage.add(record)
    return jsonify({"id": new_id}), 201


@app.delete("/battles/<int:battle_id>")
def delete_battle(battle_id):
    if storage.delete(battle_id):
        return jsonify({"deleted": battle_id})
    return jsonify({"error": "бій не знайдено"}), 404


@app.get("/report")
def report():
    records = storage.load()
    return jsonify({
        "battles": len(records),
        "average_kills": logic.average_kills(records),
        "win_rate_by_vehicle": logic.win_rate_by_vehicle(records),
        "best_battle": logic.best_battle(records),
    })


# ---- адміністративні маршрути (масові зміни даних) ----
# Захист у три шари:
#  1) nginx не пропускає /admin/ з інтернету взагалі (deploy/nginx.conf);
#  2) Flask відхиляє запит, що прийшов через Cloudflare (є CF-Connecting-IP);
#  3) Flask вимагає токен з .env у заголовку X-Admin-Token.
# Доступ до адмінки: з самого сервера (127.0.0.1:8000) або через Tailscale.

def require_admin():
    # Cloudflare додає CF-Connecting-IP до кожного запиту, що пройшов через нього,
    # і прибрати його ззовні неможливо. Є заголовок, отже запит з інтернету.
    if "CF-Connecting-IP" in request.headers:
        abort(404)
    if not ADMIN_TOKEN or request.headers.get("X-Admin-Token") != ADMIN_TOKEN:
        abort(403)


@app.get("/admin/export")
def admin_export():
    require_admin()
    return jsonify(storage.load())


@app.post("/admin/import")
def admin_import():
    require_admin()
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
        storage.add(r)
    return jsonify({"imported": len(records)}), 201


@app.delete("/admin/battles")
def admin_delete_all():
    require_admin()
    return jsonify({"deleted": storage.delete_all()})


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
    app.run(debug=True)                  # лише локально; на сервері працює gunicorn

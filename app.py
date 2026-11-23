"""Вебсервіс статистики боїв. Запуск: python app.py
Далі у браузері: http://127.0.0.1:5000/battles"""

from flask import Flask, request, jsonify
import storage
import logic

app = Flask(__name__)
app.json.ensure_ascii = False            # кирилиця в JSON без бій
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


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "такого маршруту немає"}), 404


@app.errorhandler(405)
def wrong_method(e):
    return jsonify({"error": "цей метод тут не підтримується"}), 405


if __name__ == "__main__":
    app.run(debug=True)

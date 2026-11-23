"""Логіка: перевірка, пошук і звіти. Тут немає print і input:
функції лише обчислюють і повертають результат."""

from datetime import date as _date

MODES = ("АБ", "РБ", "СБ")          # аркадні, реалістичні, симуляторні бої
RESULTS = ("перемога", "поразка")


def make_record(date, vehicle, mode, result, kills, minutes):
    """Перевіряє поля і повертає готовий запис-словник.
    Якщо щось не так, кидає ValueError з поясненням."""
    try:
        _date.fromisoformat(date)
    except (ValueError, TypeError):
        raise ValueError(f"дата має бути у форматі РРРР-ММ-ДД, а не {date!r}")

    vehicle = str(vehicle).strip()
    if vehicle == "":
        raise ValueError("техніка не може бути порожньою")
    if ";" in vehicle:
        raise ValueError("у назві техніки не можна використовувати ';'")

    mode = str(mode).strip().upper()
    if mode not in MODES:
        raise ValueError(f"режим має бути одним із {', '.join(MODES)}")

    result = str(result).strip().lower()
    if result not in RESULTS:
        raise ValueError("результат має бути 'перемога' або 'поразка'")

    try:
        kills = int(kills)
    except (ValueError, TypeError):
        raise ValueError(f"знищено має бути цілим числом, а не {kills!r}")
    if kills < 0:
        raise ValueError("знищено не може бути від'ємним")

    try:
        minutes = float(minutes)
    except (ValueError, TypeError):
        raise ValueError(f"тривалість має бути числом, а не {minutes!r}")
    if minutes <= 0:
        raise ValueError("тривалість має бути більшою за 0")

    return {"date": date, "vehicle": vehicle, "mode": mode,
            "result": result, "kills": kills, "minutes": minutes}


def find_by_vehicle(records, vehicle):
    """Бої на конкретній техніці (без різниці великих і малих літер)."""
    vehicle = vehicle.strip().lower()
    return [r for r in records if r["vehicle"].lower() == vehicle]


def win_rate_by_vehicle(records):
    """Повертає {техніка: % перемог}, округлено до 1 знака."""
    battles = {}
    wins = {}
    for r in records:
        v = r["vehicle"]
        battles[v] = battles.get(v, 0) + 1
        if r["result"] == "перемога":
            wins[v] = wins.get(v, 0) + 1
    return {v: round(wins.get(v, 0) * 100 / battles[v], 1) for v in battles}


def average_kills(records):
    """Середня кількість знищених за бій. Для порожнього списку 0."""
    if len(records) == 0:
        return 0
    return round(sum(r["kills"] for r in records) / len(records), 2)


def best_battle(records):
    """Бій з найбільшою кількістю знищених, або None, якщо боїв немає."""
    if len(records) == 0:
        return None
    return max(records, key=lambda r: r["kills"])

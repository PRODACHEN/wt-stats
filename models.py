"""Клас запису. Усередині програми ходять об'єкти Battle, а словники
з'являються лише на межі: з JSON (to_dict) і з бази (from_row)."""


class Battle:
    """Один бій: дата, техніка, режим, результат, знищено, тривалість."""

    def __init__(self, date, vehicle, mode, result, kills, minutes, battle_id=None):
        self.id = battle_id
        self.date = date
        self.vehicle = vehicle
        self.mode = mode
        self.result = result
        self.kills = int(kills)          # тут, і тільки тут, рядок стає числом
        self.minutes = float(minutes)

    def to_dict(self):
        """Для jsonify і для відповіді API."""
        return {"id": self.id, "date": self.date, "vehicle": self.vehicle,
                "mode": self.mode, "result": self.result,
                "kills": self.kills, "minutes": self.minutes}

    @staticmethod
    def from_row(row):
        """З рядка sqlite3.Row (з JOIN на vehicles) у об'єкт."""
        return Battle(row["date"], row["vehicle"], row["mode"], row["result"],
                      row["kills"], row["minutes"], row["id"])

    def is_win(self):
        return self.result == "перемога"

    def __eq__(self, other):
        return isinstance(other, Battle) and self.to_dict() == other.to_dict()

    def __repr__(self):
        return f"Battle({self.date}, {self.vehicle}, {self.result}, kills={self.kills})"

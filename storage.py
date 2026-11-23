"""Зберігання боїв у базі SQLite (файл data.db).
Значення в SQL підставляються тільки через ?, ніколи через f-рядок:
це захист від SQL-ін'єкцій."""

import sqlite3
from contextlib import contextmanager

DB = "data.db"


@contextmanager
def connect():
    """Відкриває з'єднання, після блоку with зберігає зміни і ЗАКРИВАЄ його.
    Звичайний `with sqlite3.connect(...)` лише зберігає зміни, але не закриває
    з'єднання, і на Windows файл бази лишається зайнятим."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row          # рядки можна читати як словники
    try:
        with conn:                          # commit або rollback
            yield conn
    finally:
        conn.close()


def init():
    """Створює таблицю, якщо її ще немає."""
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            mode TEXT NOT NULL,
            result TEXT NOT NULL,
            kills INTEGER NOT NULL,
            minutes REAL NOT NULL)""")


def load(vehicle=None):
    """Повертає список боїв (словників), за бажанням лише однієї техніки."""
    with connect() as conn:
        if vehicle is None:
            rows = conn.execute("SELECT * FROM battles ORDER BY date, id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM battles WHERE vehicle = ? COLLATE NOCASE ORDER BY date, id",
                (vehicle,)).fetchall()
    return [dict(row) for row in rows]


def add(record):
    """Додає бій (словник з logic.make_record) і повертає його id."""
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO battles (date, vehicle, mode, result, kills, minutes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (record["date"], record["vehicle"], record["mode"],
             record["result"], record["kills"], record["minutes"]))
        return cur.lastrowid


def delete(battle_id):
    """Видаляє бій. Повертає True, якщо такий був."""
    with connect() as conn:
        cur = conn.execute("DELETE FROM battles WHERE id = ?", (battle_id,))
        return cur.rowcount > 0

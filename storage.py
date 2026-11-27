"""Зберігання боїв у SQLite. Три таблиці:
  vehicles  — техніка (назва унікальна),
  battles   — бої, посилаються на vehicles через vehicle_id,
  audit_log — журнал дій (додавання і видалення з часом).
Значення в SQL підставляються тільки через ?, ніколи через f-рядок:
це захист від SQL-ін'єкцій."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from models import Battle

# SELECT, що повертає бої разом з назвою техніки (для Battle.from_row)
SELECT_BATTLES = """SELECT b.id, b.date, v.name AS vehicle, b.mode, b.result,
                           b.kills, b.minutes
                    FROM battles b JOIN vehicles v ON v.id = b.vehicle_id"""


def db_path():
    # Шлях береться в момент підключення: тести підставляють свою базу
    # через змінну оточення DB_PATH перед кожним тестом.
    return os.environ.get("DB_PATH", "data.db")


@contextmanager
def connect():
    """Відкриває з'єднання, після блоку with зберігає зміни і ЗАКРИВАЄ його.
    Звичайний `with sqlite3.connect(...)` лише зберігає зміни, але не закриває
    з'єднання, і на Windows файл бази лишається зайнятим."""
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row          # рядки можна читати як словники
    conn.execute("PRAGMA foreign_keys = ON")  # без цього SQLite не перевіряє зв'язки
    try:
        with conn:                          # commit або rollback
            yield conn
    finally:
        conn.close()


def old_schema(conn):
    """True, якщо в базі ще стара таблиця battles з текстовим полем vehicle."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(battles)")]
    return "vehicle" in cols


def create_tables(conn):
    """CREATE TABLE IF NOT EXISTS для всіх трьох таблиць (без commit)."""
    for sql in ("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            )""", """
            CREATE TABLE IF NOT EXISTS battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
                mode TEXT NOT NULL,
                result TEXT NOT NULL,
                kills INTEGER NOT NULL,
                minutes REAL NOT NULL
            )""", """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                action TEXT NOT NULL,
                battle_id INTEGER,
                details TEXT
            )"""):
        conn.execute(sql)


def init():
    """Створює таблиці, якщо їх ще немає."""
    with connect() as conn:
        if old_schema(conn):
            raise RuntimeError("база у старому форматі: спершу python migrate.py")
        create_tables(conn)


def log_action(conn, action, battle_id=None, details=""):
    conn.execute("INSERT INTO audit_log (ts, action, battle_id, details) VALUES (?, ?, ?, ?)",
                 (datetime.now().isoformat(timespec="seconds"), action, battle_id, details))


def vehicle_id(conn, name):
    """id техніки за назвою; якщо такої ще немає, створює."""
    row = conn.execute("SELECT id FROM vehicles WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO vehicles (name) VALUES (?)", (name,)).lastrowid


def load(vehicle=None):
    """Повертає список Battle, за бажанням лише однієї техніки."""
    with connect() as conn:
        if vehicle is None:
            rows = conn.execute(SELECT_BATTLES + " ORDER BY b.date, b.id").fetchall()
        else:
            rows = conn.execute(SELECT_BATTLES + " WHERE v.name = ? ORDER BY b.date, b.id",
                                (vehicle,)).fetchall()
    return [Battle.from_row(row) for row in rows]


def add(battle):
    """Додає Battle і повертає його id."""
    with connect() as conn:
        vid = vehicle_id(conn, battle.vehicle)
        new_id = conn.execute(
            "INSERT INTO battles (date, vehicle_id, mode, result, kills, minutes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (battle.date, vid, battle.mode, battle.result, battle.kills, battle.minutes)).lastrowid
        log_action(conn, "add", new_id, f"{battle.date} {battle.vehicle} {battle.result}")
        return new_id


def delete(battle_id):
    """Видаляє бій. Повертає True, якщо такий був."""
    with connect() as conn:
        deleted = conn.execute("DELETE FROM battles WHERE id = ?", (battle_id,)).rowcount > 0
        if deleted:
            log_action(conn, "delete", battle_id)
        return deleted


def delete_all():
    """Видаляє всі бої. Повертає, скільки було видалено."""
    with connect() as conn:
        n = conn.execute("DELETE FROM battles").rowcount
        log_action(conn, "delete_all", None, f"видалено {n}")
        return n


def vehicle_report(month=None):
    """Звіт через JOIN: по кожній техніці кількість боїв, перемог,
    % перемог і середньо знищено. month у форматі 2026-11 (необов'язково)."""
    sql = """SELECT v.name AS vehicle,
                    COUNT(*) AS battles,
                    SUM(b.result = 'перемога') AS wins,
                    ROUND(100.0 * SUM(b.result = 'перемога') / COUNT(*), 1) AS win_rate,
                    ROUND(AVG(b.kills), 2) AS average_kills
             FROM battles b
             JOIN vehicles v ON v.id = b.vehicle_id"""
    params = ()
    if month:
        sql += " WHERE b.date LIKE ?"
        params = (month + "-%",)
    sql += " GROUP BY v.id ORDER BY battles DESC, v.name"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def load_log(limit=50):
    """Останні записи журналу дій, нові зверху."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
                            (limit,)).fetchall()
    return [dict(r) for r in rows]

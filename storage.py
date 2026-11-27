"""Зберігання боїв у SQLite. Чотири таблиці:
  users     — користувачі (лише хеш пароля, роль is_admin),
  vehicles  — техніка (назва унікальна),
  battles   — бої, належать користувачу (user_id) і посилаються на vehicles,
  audit_log — журнал дій: хто, що і коли додав або видалив.
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


def columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def old_schema(conn):
    """True, якщо база ще не в форматі лаби 12 (немає users / battles.user_id)."""
    cols = columns(conn, "battles")
    return bool(cols) and "user_id" not in cols


def create_tables(conn):
    """CREATE TABLE IF NOT EXISTS для всіх трьох таблиць (без commit)."""
    for sql in ("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created TEXT NOT NULL
            )""", """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            )""", """
            CREATE TABLE IF NOT EXISTS battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
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
                user_id INTEGER,
                action TEXT NOT NULL,
                battle_id INTEGER,
                details TEXT
            )"""):
        conn.execute(sql)


def init():
    """Створює таблиці, якщо їх ще немає."""
    with connect() as conn:
        if old_schema(conn):
            raise RuntimeError("база у старому форматі: спершу python migrate.py ЛОГІН")
        create_tables(conn)


def now():
    return datetime.now().isoformat(timespec="seconds")


# ---- користувачі ----

def add_user(login, password_hash, is_admin=False):
    """Створює користувача, повертає id. Зайнятий логін: sqlite3.IntegrityError."""
    with connect() as conn:
        uid = conn.execute(
            "INSERT INTO users (login, password_hash, is_admin, created) VALUES (?, ?, ?, ?)",
            (login, password_hash, int(is_admin), now())).lastrowid
        log_action(conn, uid, "register", None, login)
        return uid


def get_user(user_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_login(login):
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
    return dict(row) if row else None


def set_admin(login, is_admin=True):
    """Для тестів і CLI. Маршруту «зробити мене адміном» немає."""
    with connect() as conn:
        return conn.execute("UPDATE users SET is_admin = ? WHERE login = ?",
                            (int(is_admin), login)).rowcount > 0


def log_action(conn, user_id, action, battle_id=None, details=""):
    conn.execute("INSERT INTO audit_log (ts, user_id, action, battle_id, details) "
                 "VALUES (?, ?, ?, ?, ?)", (now(), user_id, action, battle_id, details))


def vehicle_id(conn, name):
    """id техніки за назвою; якщо такої ще немає, створює."""
    row = conn.execute("SELECT id FROM vehicles WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO vehicles (name) VALUES (?)", (name,)).lastrowid


def load(user_id, vehicle=None):
    """Бої користувача (список Battle), за бажанням лише однієї техніки.
    user_id=None означає всі бої (лише для адмінки)."""
    where, params = [], []
    if user_id is not None:
        where.append("b.user_id = ?")
        params.append(user_id)
    if vehicle is not None:
        where.append("v.name = ?")
        params.append(vehicle)
    sql = SELECT_BATTLES
    if where:
        sql += " WHERE " + " AND ".join(where)   # склеюємо лише наші константи, значення через ?
    with connect() as conn:
        rows = conn.execute(sql + " ORDER BY b.date, b.id", params).fetchall()
    return [Battle.from_row(row) for row in rows]


def add(battle, user_id):
    """Додає Battle від імені користувача і повертає його id."""
    with connect() as conn:
        vid = vehicle_id(conn, battle.vehicle)
        new_id = conn.execute(
            "INSERT INTO battles (user_id, date, vehicle_id, mode, result, kills, minutes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, battle.date, vid, battle.mode, battle.result,
             battle.kills, battle.minutes)).lastrowid
        log_action(conn, user_id, "add", new_id, f"{battle.date} {battle.vehicle} {battle.result}")
        return new_id


def delete(battle_id, user_id):
    """Видаляє бій, лише якщо він належить користувачу. True, якщо видалено."""
    with connect() as conn:
        deleted = conn.execute("DELETE FROM battles WHERE id = ? AND user_id = ?",
                               (battle_id, user_id)).rowcount > 0
        if deleted:
            log_action(conn, user_id, "delete", battle_id)
        return deleted


def delete_all(admin_id):
    """Адмінка: видаляє всі бої всіх користувачів. Повертає кількість."""
    with connect() as conn:
        n = conn.execute("DELETE FROM battles").rowcount
        log_action(conn, admin_id, "delete_all", None, f"видалено {n}")
        return n


def vehicle_report(user_id, month=None):
    """Звіт через JOIN: по кожній техніці користувача кількість боїв, перемог,
    % перемог і середньо знищено. month у форматі 2026-11 (необов'язково)."""
    sql = """SELECT v.name AS vehicle,
                    COUNT(*) AS battles,
                    SUM(b.result = 'перемога') AS wins,
                    ROUND(100.0 * SUM(b.result = 'перемога') / COUNT(*), 1) AS win_rate,
                    ROUND(AVG(b.kills), 2) AS average_kills
             FROM battles b
             JOIN vehicles v ON v.id = b.vehicle_id
             WHERE b.user_id = ?"""
    params = (user_id,)
    if month:
        sql += " AND b.date LIKE ?"
        params = (user_id, month + "-%")
    sql += " GROUP BY v.id ORDER BY battles DESC, v.name"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def load_log(limit=50):
    """Останні записи журналу дій, нові зверху."""
    with connect() as conn:
        rows = conn.execute("""SELECT a.*, u.login FROM audit_log a
                               LEFT JOIN users u ON u.id = a.user_id
                               ORDER BY a.id DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]

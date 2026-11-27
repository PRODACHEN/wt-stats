"""Перенесення бази на нову схему. Запускається один раз на кожен крок,
лежить у репозиторії як документ того, що сталося з базою.

Лаба 11: battles(vehicle TEXT) -> vehicles + battles(vehicle_id) + audit_log.
Лаба 12: + users (хеш пароля, is_admin), battles.user_id, audit_log.user_id.
         Створюється перший користувач (ви), йому приписуються всі наявні бої.
         Адміністратора призначають вручну через sqlite3 (див. README).

Усе в одній транзакції: якщо щось піде не так, база лишиться як була.
Перед запуском бекап: python backup.py
Запуск: python migrate.py ЛОГІН   (пароль спитає; повторний запуск нічого не зламає)"""

import getpass
import sys

from werkzeug.security import generate_password_hash

import storage

with storage.connect() as conn:
    if not storage.old_schema(conn):
        print("база вже в новому форматі, переносити нічого")
        raise SystemExit(0)

if len(sys.argv) != 2 or len(sys.argv[1].strip()) < 3:
    raise SystemExit("використання: python migrate.py ЛОГІН   (логін від 3 символів)")
login = sys.argv[1].strip()
password = getpass.getpass("пароль для " + login + " (від 8 символів): ")
if len(password) < 8:
    raise SystemExit("пароль має бути від 8 символів")
if getpass.getpass("ще раз: ") != password:
    raise SystemExit("паролі не збігаються")

with storage.connect() as conn:
    conn.execute("BEGIN")                 # інакше ALTER TABLE не відкотиться
    old_cols = storage.columns(conn, "battles")
    before = conn.execute("SELECT COUNT(*) FROM battles").fetchone()[0]
    conn.execute("ALTER TABLE battles RENAME TO battles_old")
    if storage.columns(conn, "audit_log") and "user_id" not in storage.columns(conn, "audit_log"):
        conn.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER")
    storage.create_tables(conn)           # users, vehicles, нова battles, audit_log

    uid = conn.execute(
        "INSERT INTO users (login, password_hash, is_admin, created) VALUES (?, ?, 0, ?)",
        (login, generate_password_hash(password), storage.now())).lastrowid

    if "vehicle" in old_cols:             # база ще з лаби 10: техніка текстом
        for (name,) in conn.execute("SELECT DISTINCT vehicle FROM battles_old").fetchall():
            storage.vehicle_id(conn, name)
        conn.execute("""INSERT INTO battles (id, user_id, date, vehicle_id, mode, result, kills, minutes)
                        SELECT o.id, ?, o.date, v.id, o.mode, o.result, o.kills, o.minutes
                        FROM battles_old o JOIN vehicles v ON v.name = o.vehicle""", (uid,))
    else:                                 # база з лаби 11: уже є vehicle_id
        conn.execute("""INSERT INTO battles (id, user_id, date, vehicle_id, mode, result, kills, minutes)
                        SELECT id, ?, date, vehicle_id, mode, result, kills, minutes
                        FROM battles_old""", (uid,))

    after = conn.execute("SELECT COUNT(*) FROM battles").fetchone()[0]
    if after != before:
        # виняток усередині with -> rollback, база повертається як була
        raise RuntimeError(f"було {before} боїв, перенесено {after}: зміни скасовано")
    conn.execute("DROP TABLE battles_old")
    storage.log_action(conn, uid, "migrate", None, f"користувач {login}, перенесено {after} боїв")

print(f"готово: створено користувача {login} (id {uid}), йому приписано {after} боїв")
print(f"зробити адміністратором: sqlite3 data.db \"UPDATE users SET is_admin = 1 WHERE login = '{login}';\"")

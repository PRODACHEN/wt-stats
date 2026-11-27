"""Одноразове перенесення бази на нову схему (лаба 11).
Було:  battles(id, date, vehicle TEXT, mode, result, kills, minutes)
Стало: vehicles(id, name) + battles(..., vehicle_id -> vehicles.id) + audit_log.
Усе в одній транзакції: якщо щось піде не так, база лишиться як була.
Перед запуском зробіть бекап: python backup.py
Запуск: python migrate.py   (повторний запуск нічого не зламає)"""

import storage

with storage.connect() as conn:
    if not storage.old_schema(conn):
        print("база вже в новому форматі, переносити нічого")
        raise SystemExit(0)

    conn.execute("BEGIN")                 # інакше ALTER TABLE не відкотиться
    before = conn.execute("SELECT COUNT(*) FROM battles").fetchone()[0]
    conn.execute("ALTER TABLE battles RENAME TO battles_old")
    storage.create_tables(conn)           # vehicles, нова battles, audit_log

    for (name,) in conn.execute("SELECT DISTINCT vehicle FROM battles_old").fetchall():
        storage.vehicle_id(conn, name)
    conn.execute("""INSERT INTO battles (id, date, vehicle_id, mode, result, kills, minutes)
                    SELECT o.id, o.date, v.id, o.mode, o.result, o.kills, o.minutes
                    FROM battles_old o JOIN vehicles v ON v.name = o.vehicle""")
    after = conn.execute("SELECT COUNT(*) FROM battles").fetchone()[0]
    if after != before:
        # виняток усередині with -> rollback, стара таблиця повертається
        raise RuntimeError(f"було {before} боїв, перенесено {after}: зміни скасовано")
    conn.execute("DROP TABLE battles_old")
    vehicles = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    storage.log_action(conn, "migrate", None, f"перенесено {after} боїв")

print(f"готово: перенесено {after} боїв, техніки: {vehicles} шт.")

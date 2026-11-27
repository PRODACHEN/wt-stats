"""Копіює базу в теку backups поруч зі скриптом, з датою в назві.
Зайві копії старші за 14 днів видаляє. Запуск щодня через cron (див. README)."""
import datetime
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
# з лаби 13 база лежить у data/ (це том Docker-контейнера)
DB = os.path.join(BASE, "data", "data.db")
if not os.path.exists(DB):
    DB = os.path.join(BASE, "data.db")
BACKUPS = os.path.join(BASE, "backups")
KEEP_DAYS = 14

os.makedirs(BACKUPS, exist_ok=True)
target = os.path.join(BACKUPS, f"data-{datetime.date.today()}.db")
src = sqlite3.connect(DB)
dst = sqlite3.connect(target)
src.backup(dst)                        # коректна копія навіть під час роботи сервісу
dst.close()
src.close()
print("збережено", target)

limit = datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)
for name in os.listdir(BACKUPS):
    try:
        day = datetime.date.fromisoformat(name[len("data-"):-len(".db")])
    except ValueError:
        continue
    if day < limit:
        os.remove(os.path.join(BACKUPS, name))
        print("видалено стару копію", name)

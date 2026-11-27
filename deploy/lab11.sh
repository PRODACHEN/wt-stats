#!/bin/bash
# Лаба 11 на сервері. Запуск з теки проєкту ПІСЛЯ git pull:
#   bash deploy/lab11.sh
set -e
cd "$(dirname "$0")/.."

echo "== залежності (pytest)"
./venv/bin/pip install -r requirements.txt -q

echo "== бекап перед міграцією"
./venv/bin/python backup.py

echo "== міграція бази: vehicles + battles(vehicle_id) + audit_log"
./venv/bin/python migrate.py

echo "== тести"
./venv/bin/python -m pytest -q

echo "== перезапуск сервісу"
sudo systemctl restart wt-stats
sleep 2
systemctl is-active wt-stats

TOKEN=$(grep ADMIN_TOKEN .env | cut -d= -f2-)
echo "== перевірки"
echo -n "GET /battles (чекаємо 200):          "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/battles
echo -n "GET /report/vehicles (чекаємо 200):  "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/report/vehicles
echo -n "GET /admin/log з токеном (200):      "; curl -s -o /dev/null -w "%{http_code}\n" -H "X-Admin-Token: $TOKEN" http://127.0.0.1:8000/admin/log
echo "звіт по техніці:"; curl -s http://127.0.0.1:8000/report/vehicles; echo
echo "ГОТОВО"

#!/bin/bash
# Лаба 12 на сервері: користувачі, вхід, ролі. Запуск з теки проєкту ПІСЛЯ git pull:
#   bash deploy/lab12.sh ЛОГІН        (пароль для ЛОГІН спитає migrate.py)
set -e
cd "$(dirname "$0")/.."
LOGIN="$1"
if [ -z "$LOGIN" ]; then echo "використання: bash deploy/lab12.sh ЛОГІН"; exit 1; fi

echo "== залежності"
./venv/bin/pip install -r requirements.txt -q

echo "== бекап перед міграцією"
./venv/bin/python backup.py

echo "== .env: SECRET_KEY для сесій, ADMIN_TOKEN більше не потрібен"
touch .env && chmod 600 .env
if ! grep -q '^SECRET_KEY=' .env; then
    echo "SECRET_KEY=$(./venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
    echo "додано SECRET_KEY"
fi
sed -i '/^ADMIN_TOKEN=/d' .env
echo "у .env тепер: $(cut -d= -f1 .env | tr '\n' ' ')"

echo "== міграція бази: users + battles.user_id + audit_log.user_id"
./venv/bin/python migrate.py "$LOGIN"

echo "== тести"
./venv/bin/python -m pytest -q

echo "== перезапуск сервісу"
sudo systemctl restart wt-stats
sleep 2
systemctl is-active wt-stats

echo "== перевірки"
echo -n "GET /battles без входу (чекаємо 401):      "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/battles
echo -n "POST /login з неправильним паролем (401):  "; curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/login -H "Content-Type: application/json" -d '{"login": "'"$LOGIN"'", "password": "wrong-password"}'
echo -n "GET /admin/log без входу (чекаємо 401):    "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/admin/log
echo -n "хеш пароля в базі починається з:           "; sqlite3 data.db "SELECT substr(password_hash, 1, 7) FROM users WHERE login = '$LOGIN';"
echo "ГОТОВО. Тепер зробіть себе адміністратором:"
echo "  sqlite3 data.db \"UPDATE users SET is_admin = 1 WHERE login = '$LOGIN';\""

#!/bin/bash
# Лаба 10 на сервері. Запуск з теки проєкту ПІСЛЯ git pull:
#   bash deploy/lab10.sh
set -e
cd "$(dirname "$0")/.."

echo "== залежності (python-dotenv)"
./venv/bin/pip install -r requirements.txt -q

echo "== .env з токеном адміна"
if [ ! -f .env ]; then
    echo "ADMIN_TOKEN=$(./venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
    chmod 600 .env
    echo "створено .env (токен подивитись: cat .env)"
else
    echo ".env уже є, не чіпаю"
fi

echo "== тести"
./venv/bin/python tests.py

echo "== nginx: /admin/ з інтернету -> 404"
sudo cp deploy/nginx.conf /etc/nginx/sites-available/wt-stats
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart wt-stats

echo "== резервна копія зараз і щодня о 20:00 (cron)"
./venv/bin/python backup.py
LINE="0 20 * * * cd $PWD && $PWD/venv/bin/python $PWD/backup.py >> $PWD/backups/backup.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'backup.py' ; echo "$LINE" ) | crontab -
crontab -l | grep backup.py

echo "== fail2ban для ssh"
sudo apt install -y fail2ban > /dev/null
sudo tee /etc/fail2ban/jail.local > /dev/null <<'JAIL'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
JAIL
sudo systemctl enable --now fail2ban
sudo systemctl restart fail2ban
sleep 2
sudo fail2ban-client status sshd | head -n 5

sleep 1
echo "== перевірки"
TOKEN=$(grep ADMIN_TOKEN .env | cut -d= -f2-)
echo -n "локально без токена (чекаємо 403): "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/admin/export
echo -n "локально з токеном (чекаємо 200):  "; curl -s -o /dev/null -w "%{http_code}\n" -H "X-Admin-Token: $TOKEN" http://127.0.0.1:8000/admin/export
echo -n "через nginx (чекаємо 404):         "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/admin/export
echo "ГОТОВО"

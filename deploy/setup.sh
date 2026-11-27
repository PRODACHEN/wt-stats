#!/bin/bash
# Перше розгортання на чистому Ubuntu 24.04. Запуск з теки проєкту:
#   bash deploy/setup.sh
set -e
cd "$(dirname "$0")/.."

echo "== пакети"
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip nginx ufw sqlite3

echo "== віртуальне оточення і залежності"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

echo "== перевірка тестів"
./venv/bin/python -m pytest -q

echo "== служба systemd (USERNAME -> $USER)"
sed "s/USERNAME/$USER/g" deploy/wt-stats.service | sudo tee /etc/systemd/system/wt-stats.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now wt-stats
sudo systemctl restart wt-stats

echo "== nginx"
sudo cp deploy/nginx.conf /etc/nginx/sites-available/wt-stats
sudo ln -sf /etc/nginx/sites-available/wt-stats /etc/nginx/sites-enabled/wt-stats
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "== фаєрвол: лише 22, 80, 443"
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status

sleep 2
echo "== перевірка"
curl -s http://127.0.0.1/battles && echo && echo "ГОТОВО: сервіс працює через nginx"

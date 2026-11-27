#!/bin/bash
# Лаба 13 на сервері: перехід із systemd на Docker. Запуск з теки проєкту ПІСЛЯ git pull:
#   bash deploy/lab13.sh
# Перший запуск ставить Docker і просить перезайти в SSH; другий робить решту.
set -e
cd "$(dirname "$0")/.."

if ! command -v docker > /dev/null; then
    echo "== встановлення Docker"
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo
    echo "Docker встановлено. ЗАКРИЙТЕ вікно SSH, відкрийте знову і виконайте:"
    echo "  cd wt-stats && bash deploy/lab13.sh"
    exit 0
fi
if ! docker info > /dev/null 2>&1; then
    echo "немає доступу до Docker: перезайдіть у SSH (група docker застосовується після входу)"
    exit 1
fi

echo "== база в теку data/ (том контейнера)"
mkdir -p data
if [ -f data.db ] && [ ! -f data/data.db ]; then
    ./venv/bin/python backup.py
    mv data.db data/data.db
    echo "data.db перенесено в data/"
fi
ls -l data/

echo "== зупинка старого сервісу systemd (порт 8000 звільняється для контейнера)"
sudo systemctl disable --now wt-stats || true

echo "== збірка і запуск контейнера"
docker compose up -d --build

echo "== чекаємо /health"
for i in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:8000/health; then echo; break; fi
    sleep 2
done
docker compose ps

echo "== перевірки"
echo -n "GET /health (200):               "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health
echo -n "GET /battles без входу (401):    "; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/battles
echo -n "через nginx /health (200):       "; curl -sk -o /dev/null -w "%{http_code}\n" https://127.0.0.1/health -H "Host: api.prodachen.pp.ua"
echo "бекап тепер бере базу з data/: $(./venv/bin/python backup.py)"
echo "ГОТОВО"

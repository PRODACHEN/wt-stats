# Статистика боїв War Thunder

Назва:     Статистика боїв War Thunder
Для кого:  для мене, щоб бачити, на якій техніці я граю найкраще
Запис:     дата, техніка, режим, результат, знищено, тривалість (хв)
Операції:  додати, показати всі, знайти за технікою, видалити
Звіти:     % перемог по техніці, середня кількість знищених, найкращий бій

Режим: АБ, РБ або СБ. Результат: перемога або поразка.

## Встановлення

    python -m venv venv
    venv\Scripts\activate            (Windows)
    source venv/bin/activate         (Linux)
    pip install -r requirements.txt

## Вебсервіс

    python app.py

Сервер працює на http://127.0.0.1:5000

| Метод  | Маршрут                    | Що робить                  |
|--------|----------------------------|----------------------------|
| GET    | /battles                   | усі бої                    |
| GET    | /battles?vehicle=F/A-18C   | бої на одній техніці       |
| POST   | /battles                   | додати бій (JSON)          |
| DELETE | /battles/<id>              | видалити бій               |
| GET    | /report                    | звіт                       |

Приклади curl:

    curl http://127.0.0.1:5000/battles
    curl "http://127.0.0.1:5000/battles?vehicle=F/A-18C"
    curl -X POST http://127.0.0.1:5000/battles -H "Content-Type: application/json" -d '{"date": "2026-11-23", "vehicle": "F/A-18C", "mode": "РБ", "result": "перемога", "kills": 4, "minutes": 12}'
    curl -X DELETE http://127.0.0.1:5000/battles/1
    curl -i http://127.0.0.1:5000/report

Помилки: POST без тіла або з текстом замість числа дає 400,
DELETE неіснуючого id дає 404.

## Консоль

    python cli.py add 2026-11-23 "F/A-18C" РБ перемога 4 12
    python cli.py list
    python cli.py find "F/A-18C"
    python cli.py report
    python cli.py delete 1
    python tests.py

## Дані

База SQLite data.db, таблиця battles:
id, date, vehicle, mode, result, kills, minutes.

## Розгортання (Google Cloud, Ubuntu 24.04)

Машина e2-micro, регіон us-central1, статичний IP, галочки HTTP/HTTPS.
На сервері:

    git clone https://github.com/PRODACHEN/wt-stats.git
    cd wt-stats
    bash deploy/setup.sh

Скрипт ставить пакети (git, python3-venv, nginx, ufw, sqlite3), створює venv,
запускає тести, ставить службу systemd (deploy/wt-stats.service, gunicorn на
127.0.0.1:8000), nginx (deploy/nginx.conf) і фаєрвол ufw (лише 22, 80, 443).

HTTPS:

    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/local/bin/certbot
    sudo certbot --nginx -d api.prodachen.pp.ua

Оновлення коду:

    git pull && sudo systemctl restart wt-stats

Логи: sudo journalctl -u wt-stats -n 50

## Фронтенд і Cloudflare

Сайт: https://prodachen.pp.ua (Netlify, тека frontend/), API: https://api.prodachen.pp.ua.

- Netlify: Base directory і Publish directory = frontend, build command порожній.
- Cloudflare: NS домену на Cloudflare, A api через проксі (оранжева хмарка),
  SSL/TLS Full (strict), Always Use HTTPS, rate limiting на /battles,
  Bypass cache для api.prodachen.pp.ua/*.
- CORS у app.py дозволяє лише https://prodachen.pp.ua.
- Сервер приймає 80/443 лише від Cloudflare: bash deploy/cloudflare.sh
- Дані у фронтенді виводяться лише через textContent (захист від XSS).

Локальна перевірка фронтенду: python -m http.server 8080 у теці frontend/,
у app.py тимчасово додати "http://localhost:8080" до origins.

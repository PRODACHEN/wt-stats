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

Адміністративні маршрути (лише з сервера або через Tailscale, з токеном):

| Метод  | Маршрут          | Що робить                         |
|--------|------------------|-----------------------------------|
| GET    | /admin/export    | вивантажити всі бої (JSON)        |
| POST   | /admin/import    | завантажити масив боїв (JSON)     |
| DELETE | /admin/battles   | видалити всі бої                  |

    curl -H "X-Admin-Token: ТОКЕН" http://127.0.0.1:8000/admin/export

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

## Безпека (лаба 10)

Секрети: токен адміна лежить у `.env` (його немає в git, шаблон `.env.example`).
Створити: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Перевірка, що секрет не витік: `git log -p | grep -i token` порожнє.

Адмінка захищена трьома шарами:
1. nginx відповідає 404 на `/admin/` з інтернету (`deploy/nginx.conf`);
2. Flask відповідає 404, якщо є заголовок `CF-Connecting-IP` (запит прийшов через Cloudflare);
3. Flask вимагає заголовок `X-Admin-Token` з `.env`, інакше 403.

Доступ до адмінки з телефона/ноутбука: Tailscale на сервері
(`sudo tailscale up`, потім `sudo tailscale serve --bg --https=8443 8000`), адреса
`https://wt-stats.tail15dd4a.ts.net:8443` видна лише з моїх пристроїв у Tailscale.
Порт 8443, а не стандартний 443: на 443 працює nginx для Cloudflare, і якщо
`tailscale serve` займе 443, nginx не відкриє порт і Cloudflare віддасть помилку 521.

Блокування адрес: Cloudflare, Security → WAF → Custom rules, IP Source Address equals ... → Block.
ssh захищений fail2ban (5 помилок за 10 хв → бан на годину).

Резервні копії: `backup.py` щодня о 20:00 через cron (`deploy/lab10.sh` додає рядок),
копії в `backups/` (не в git), зберігаються 14 днів. Відновлення перевірено:

    python -c "import sqlite3; print(sqlite3.connect('backups/data-2026-11-27.db').execute('SELECT COUNT(*) FROM battles').fetchone())"

Розгортання змін лаби 10 на сервері: `git pull && bash deploy/lab10.sh`
(скрипт не перезаписує робочий конфіг nginx з HTTPS від certbot, лише перевіряє його).

### Аудит

| Загроза | Як перевірено | Стан |
|---------|---------------|------|
| SQL-ін'єкція | пошук `'; DROP TABLE battles; --` у tests.py | закрито: параметри `?` у всіх запитах |
| XSS у фронтенді | бій з vehicle = `<img src=x onerror=alert(1)>` | закрито: дані виводяться через textContent |
| сервер розробки в інтернеті | служба systemd запускає gunicorn | закрито: debug=True лише при `python app.py` локально |
| доступ в обхід Cloudflare | `curl http://IP_СЕРВЕРА` ззовні не відповідає | закрито: ufw пускає 80/443 лише з адрес Cloudflare, gunicorn слухає 127.0.0.1 |
| флуд запитами | 100 POST у циклі через https://api... | закрито: rate limiting у Cloudflare на /battles |
| підбір пароля ssh | `sudo fail2ban-client status sshd` | закрито: fail2ban |
| адмінка з інтернету | https://api.prodachen.pp.ua/admin/export з телефона → 404; https://wt-stats.tail15dd4a.ts.net:8443/admin/export без токена → 403 | закрито: nginx, CF-Connecting-IP, токен |
| секрети в git | `git log -p \| grep -i token`; `git log --all --name-only \| grep env$` | закрито: .env у .gitignore |
| втрата даних | видалити копію data.db, відновити з backups/ | закрито: backup.py за розкладом; раз на тиждень копіюю бекап на ноутбук (`scp`) |
| вразливі бібліотеки | `pip install pip-audit`, `pip-audit -r requirements.txt` | перевіряю, оновлюю версії в requirements.txt |
| видалення одного бою без входу | DELETE /battles/<id> з фронтенду | відкрито: прийнятно, поки сервіс лише мій; закриється в лабі 12 (користувачі й права) |

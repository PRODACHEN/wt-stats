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
| POST   | /register                  | реєстрація {login, password} |
| POST   | /login                     | вхід {login, password}     |
| POST   | /logout                    | вихід                      |
| GET    | /me                        | хто я                      |
| GET    | /battles                   | мої бої                    |
| GET    | /battles?vehicle=F/A-18C   | бої на одній техніці       |
| POST   | /battles                   | додати бій (JSON)          |
| DELETE | /battles/<id>              | видалити бій               |
| GET    | /report                    | звіт                       |
| GET    | /report/vehicles?month=2026-11 | звіт по техніці (JOIN), місяць необов'язковий |

Приклади curl:

    curl http://127.0.0.1:5000/battles
    curl "http://127.0.0.1:5000/battles?vehicle=F/A-18C"
    curl -X POST http://127.0.0.1:5000/battles -H "Content-Type: application/json" -d '{"date": "2026-11-23", "vehicle": "F/A-18C", "mode": "РБ", "result": "перемога", "kills": 4, "minutes": 12}'
    curl -X DELETE http://127.0.0.1:5000/battles/1
    curl -i http://127.0.0.1:5000/report

Усі маршрути з даними працюють лише після входу (cookie сесії), інакше 401.
Кожен користувач бачить і видаляє тільки свої бої; чужий бій дає 404.

Адміністративні маршрути (лише для is_admin = 1 і лише через Tailscale, не через Cloudflare):

| Метод  | Маршрут          | Що робить                         |
|--------|------------------|-----------------------------------|
| GET    | /admin/export    | вивантажити всі бої (JSON)        |
| POST   | /admin/import    | завантажити масив боїв (JSON)     |
| DELETE | /admin/battles   | видалити всі бої                  |
| GET    | /admin/log?limit=50 | журнал дій (нові зверху)       |

    curl -c admin.txt -X POST https://wt-stats.tail15dd4a.ts.net:8443/login -H "Content-Type: application/json" -d '{"login": "ЛОГІН", "password": "..."}'
    curl -b admin.txt https://wt-stats.tail15dd4a.ts.net:8443/admin/log
    curl -b admin.txt https://api.prodachen.pp.ua/admin/log        # через Cloudflare: 404

Перевірка входу через curl з файлом cookie:

    curl -c jar.txt -X POST https://api.prodachen.pp.ua/login -H "Content-Type: application/json" -d '{"login": "ЛОГІН", "password": "..."}'
    curl -b jar.txt https://api.prodachen.pp.ua/battles
    curl https://api.prodachen.pp.ua/battles                       # без cookie: 401

Помилки: POST без тіла або з текстом замість числа дає 400,
DELETE неіснуючого id дає 404.

## Консоль

    python cli.py add 2026-11-23 "F/A-18C" РБ перемога 4 12
    python cli.py list
    python cli.py find "F/A-18C"
    python cli.py report
    python cli.py delete 1
    python cli.py log
    python cli.py -u ЛОГІН list      (від імені іншого користувача; без -u перший адмін)

## Тести (pytest)

    python -m pytest -v

tests/test_logic.py перевіряє logic.py і клас Battle, tests/test_app.py перевіряє
маршрути Flask через тестовий клієнт. Кожен тест маршрутів працює на своїй
порожній базі (DB_PATH у тимчасовій теці), ваші дані в data.db не чіпаються.

## Дані (лаба 11)

Запис бою представлений класом `Battle` (models.py). Словники лише на межі:
`to_dict()` для JSON, `Battle.from_row()` з бази. logic.py працює з об'єктами.

База SQLite data.db (`PRAGMA foreign_keys = ON` при кожному підключенні):

    users(id, login UNIQUE, password_hash, is_admin, created)   -- лише хеш (scrypt), не пароль
    vehicles(id, name UNIQUE)
    battles(id, user_id -> users.id, date, vehicle_id -> vehicles.id, mode, result, kills, minutes)
    audit_log(id, ts, user_id, action, battle_id, details)       -- хто, що і коли

Звіт через JOIN (storage.vehicle_report, маршрут /report/vehicles):

    SELECT v.name, COUNT(*), SUM(b.result = 'перемога'), AVG(b.kills)
    FROM battles b JOIN vehicles v ON v.id = b.vehicle_id
    WHERE b.date LIKE '2026-11-%' GROUP BY v.id;

Перехід зі старих схем: `migrate.py` (лаба 11: техніка в окрему таблицю;
лаба 12: користувачі, усі наявні бої приписуються першому користувачу).
Одна транзакція, кількість боїв до і після звіряється. Лежить у репозиторії
як документ того, що сталося з базою.

## Користувачі (лаба 12)

Розгортання на сервері: `git pull && bash deploy/lab12.sh ЛОГІН` (бекап, SECRET_KEY у .env,
ADMIN_TOKEN з .env видаляється, міграція з паролем, тести, перезапуск, перевірки).

Першого адміністратора призначають вручну, маршруту «зробити мене адміном» немає:

    sqlite3 data/data.db "UPDATE users SET is_admin = 1 WHERE login = 'ЛОГІН';"

Сесія: підписаний cookie Flask (ключ SECRET_KEY у .env), Secure, HttpOnly, SameSite=Lax.
Фронтенд на prodachen.pp.ua, API на api.prodachen.pp.ua: CORS з supports_credentials=True
і `credentials: "include"` у кожному fetch. SESSION_COOKIE_DOMAIN не задається, тому cookie
працює і на адресі Tailscale.

## Запуск сервера (лаба 13: Docker, GitHub Actions, моніторинг)

Сервер: Google Cloud e2-micro, Ubuntu 24.04, тека `~/wt-stats`. Це окрема робоча копія
лише для сервісу: код я пишу на ноутбуці, на сервер він потрапляє тільки через git.

    Cloudflare -> nginx :443 -> 127.0.0.1:8000 -> Docker-контейнер (gunicorn, app:app)
    Tailscale serve :8443 ----^                     база: ./data/data.db (том /data)

- `Dockerfile`: python:3.12-slim, залежності, gunicorn на 0.0.0.0:8000 усередині контейнера.
- `compose.yaml`: порт лише на 127.0.0.1:8000 сервера, `restart: always`, `.env` з SECRET_KEY,
  том `./data:/data` (база переживає `docker compose down && docker compose up -d --build`).
- `.dockerignore`: venv, .git, бази, .env, backups, data, tests, frontend не потрапляють в образ.
- nginx і `tailscale serve` не змінились: вони як і раніше ходять на 127.0.0.1:8000.

Перехід із systemd на Docker (один раз): `git pull && bash deploy/lab13.sh`.

Корисне:

    docker compose ps                  # стан
    docker compose logs -f api         # логи
    docker compose restart api
    docker compose exec api python cli.py log
    sqlite3 data/data.db "UPDATE users SET is_admin = 1 WHERE login = 'ЛОГІН';"

### Автоматичні тести і деплой

`.github/workflows/ci.yml`: на кожен push у master GitHub запускає pytest на своїй машині
(job test). Якщо тести зелені, job deploy виконується на self-hosted runner на сервері:
`git pull` у `~/wt-stats`, `docker compose up -d --build` і перевірка `/health`.
Червоний тест блокує деплой (`needs: test`).

Runner (Settings → Actions → Runners → New self-hosted runner → Linux x64) стоїть у
`~/actions-runner` на сервері, поза текою проєкту, і працює як служба:
`sudo ./svc.sh install && sudo ./svc.sh start`. Стан: `sudo ./svc.sh status`.

Безпека runner: репозиторій публічний (портфоліо), тому в Settings → Actions → General
увімкнено «Require approval for all external contributors»; workflow з чужих pull request
не схвалюю.

### Моніторинг

`GET /health` без входу: `{"status": "ok"}` або 503 `{"status": "db_error"}`, якщо база не відповідає.
UptimeRobot, монітор HTTP(s) на https://api.prodachen.pp.ua/health кожні 5 хвилин,
сповіщення на email. Кеш Cloudflare для api.prodachen.pp.ua вимкнений (Bypass cache),
тож монітор бачить сервер, а не кеш. Перевірено: `docker compose stop` → лист про падіння,
`docker compose start` → лист про відновлення.

## Розгортання до лаби 13 (історія: systemd + gunicorn)

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

Секрети: ключ підпису сесій SECRET_KEY лежить у `.env` (його немає в git, шаблон `.env.example`).
Створити: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Перевірка, що секрет не витік: `git log -p | grep -iE "secret_key=|admin_token="` показує лише шаблон.
Статичний ADMIN_TOKEN з лаби 10 видалений з коду і з .env (у git він ніколи не потрапляв).

Адмінка захищена трьома шарами:
1. nginx відповідає 404 на `/admin/` з інтернету (`deploy/nginx.conf`);
2. Flask відповідає 404, якщо є заголовок `CF-Connecting-IP` (запит прийшов через Cloudflare);
3. Flask вимагає сесію користувача з is_admin = 1: без входу 401, звичайний користувач 403.

Доступ до адмінки з телефона/ноутбука: Tailscale на сервері
(`sudo tailscale up`, потім `sudo tailscale serve --bg --https=8443 8000`), адреса
`https://wt-stats.tail15dd4a.ts.net:8443` видна лише з моїх пристроїв у Tailscale.
Порт 8443, а не стандартний 443: на 443 працює nginx для Cloudflare, і якщо
`tailscale serve` займе 443, nginx не відкриє порт і Cloudflare віддасть помилку 521.

Блокування адрес: Cloudflare, Security → WAF → Custom rules, IP Source Address equals ... → Block.
ssh захищений fail2ban (5 помилок за 10 хв → бан на годину).

Резервні копії: `backup.py` (бере базу з data/, якщо вона там) щодня о 20:00 через cron,
копії в `backups/` (не в git), зберігаються 14 днів. Відновлення перевірено:

    python -c "import sqlite3; print(sqlite3.connect('backups/data-2026-11-27.db').execute('SELECT COUNT(*) FROM battles').fetchone())"

Рядок cron: `0 20 * * * cd ~/wt-stats && venv/bin/python backup.py >> backups/backup.log 2>&1`.

### Аудит

| Загроза | Як перевірено | Стан |
|---------|---------------|------|
| SQL-ін'єкція | пошук `'; DROP TABLE battles; --` у tests.py | закрито: параметри `?` у всіх запитах |
| XSS у фронтенді | бій з vehicle = `<img src=x onerror=alert(1)>` | закрито: дані виводяться через textContent |
| сервер розробки в інтернеті | контейнер запускає gunicorn | закрито: debug=True лише при `python app.py` локально |
| код з чужого pull request на runner | Settings → Actions → General | закрито: схвалення для всіх зовнішніх контриб'юторів |
| доступ в обхід Cloudflare | `curl http://IP_СЕРВЕРА` ззовні не відповідає | закрито: ufw пускає 80/443 лише з адрес Cloudflare, gunicorn слухає 127.0.0.1 |
| флуд запитами | 100 POST у циклі через https://api... | закрито: rate limiting у Cloudflare на /battles |
| підбір пароля ssh | `sudo fail2ban-client status sshd` | закрито: fail2ban |
| адмінка з інтернету | https://api.prodachen.pp.ua/admin/export з телефона → 404; через Tailscale без входу → 401, звичайний користувач → 403 | закрито: nginx, CF-Connecting-IP, роль is_admin |
| секрети в git | `git log -p \| grep -iE "secret_key=\|admin_token="`; `git log --all --name-only \| grep env$` | закрито: .env у .gitignore |
| втрата даних | видалити копію data.db, відновити з backups/ | закрито: backup.py за розкладом; раз на тиждень копіюю бекап на ноутбук (`scp`) |
| вразливі бібліотеки | `pip install pip-audit`, `pip-audit -r requirements.txt` | перевіряю, оновлюю версії в requirements.txt |
| чужі дані | другий користувач: GET /battles, DELETE /battles/<чужий id> | закрито: WHERE user_id = ?, чужий запис дає 404 |
| паролі в базі | `SELECT password_hash FROM users` | закрито: лише хеш scrypt (werkzeug) |
| перебір логінів | неправильний пароль і неіснуючий логін | закрито: однакова відповідь 401 |
| підбір пароля | багато POST /login | частково: пароль від 8 символів, повільний scrypt; rate limiting Cloudflare розширити на /login |
| крадіжка сесії | cookie у DevTools | закрито: HttpOnly, Secure, SameSite=Lax, підпис SECRET_KEY |

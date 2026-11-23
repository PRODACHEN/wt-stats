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

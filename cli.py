"""Консольний інтерфейс (дані тепер у базі data.db). Приклади:
python cli.py add 2026-11-23 "F/A-18C" РБ перемога 4 12
python cli.py list
python cli.py find "F/A-18C"
python cli.py report
python cli.py delete 3        (3 це id з команди list)
python cli.py log             (журнал дій)
"""

import sys
import storage
import logic

USAGE = ("використання:\n"
         "  python cli.py add ДАТА ТЕХНІКА РЕЖИМ РЕЗУЛЬТАТ ЗНИЩЕНО ХВИЛИНИ\n"
         "  python cli.py list\n"
         "  python cli.py find ТЕХНІКА\n"
         "  python cli.py report\n"
         "  python cli.py delete ID\n"
         "  python cli.py log")


def print_battle(r):
    print(f"{r.id:>3}. {r.date}  {r.vehicle:<14} {r.mode:<3} "
          f"{r.result:<9} знищено: {r.kills:<3} {r.minutes:g} хв")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return
    command = sys.argv[1]
    storage.init()

    if command == "add":
        if len(sys.argv) != 8:
            print(USAGE)
            return
        try:
            record = logic.make_record(*sys.argv[2:8])
        except ValueError as e:
            print("помилка:", e)
            return
        new_id = storage.add(record)
        print("бій додано, id", new_id)

    elif command == "list":
        records = storage.load()
        if not records:
            print("боїв ще немає")
        for r in records:
            print_battle(r)

    elif command == "find":
        if len(sys.argv) < 3:
            print("вкажіть техніку: python cli.py find ТЕХНІКА")
            return
        found = storage.load(sys.argv[2])
        if not found:
            print("боїв на цій техніці не знайдено")
        for r in found:
            print_battle(r)

    elif command == "report":
        records = storage.load()
        if not records:
            print("боїв ще немає, звіту не буде")
            return
        print(f"Усього боїв: {len(records)}")
        print(f"Середньо знищено за бій: {logic.average_kills(records)}")
        print("Відсоток перемог по техніці:")
        for vehicle, rate in logic.win_rate_by_vehicle(records).items():
            print(f"  {vehicle:<14} {rate:>5}%")
        best = logic.best_battle(records)
        print(f"Найкращий бій: {best.date}, {best.vehicle}, знищено {best.kills}")
        print("По техніці (звіт через JOIN):")
        for row in storage.vehicle_report():
            print(f"  {row['vehicle']:<14} боїв {row['battles']:<3} "
                  f"перемог {row['win_rate']}%  сер. знищено {row['average_kills']}")

    elif command == "delete":
        try:
            battle_id = int(sys.argv[2])
        except (IndexError, ValueError):
            print("вкажіть id бою з команди list: python cli.py delete ID")
            return
        if storage.delete(battle_id):
            print("видалено бій", battle_id)
        else:
            print("бою з таким id немає")

    elif command == "log":
        for row in storage.load_log(20):
            print(f"{row['ts']}  {row['action']:<10} {row['battle_id'] or '':<4} {row['details'] or ''}")

    else:
        print("невідома команда:", command)
        print(USAGE)


if __name__ == "__main__":
    main()

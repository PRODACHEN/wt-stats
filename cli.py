"""Консольний інтерфейс. Приклади:
python cli.py add 2026-11-23 "F/A-18C" РБ перемога 4 12
python cli.py list
python cli.py find "F/A-18C"
python cli.py report
python cli.py delete 3
"""

import sys
import storage
import logic

FILE = "data.txt"
USAGE = ("використання:\n"
         "  python cli.py add ДАТА ТЕХНІКА РЕЖИМ РЕЗУЛЬТАТ ЗНИЩЕНО ХВИЛИНИ\n"
         "  python cli.py list\n"
         "  python cli.py find ТЕХНІКА\n"
         "  python cli.py report\n"
         "  python cli.py delete НОМЕР")


def print_battle(number, r):
    print(f"{number:>3}. {r['date']}  {r['vehicle']:<14} {r['mode']:<3} "
          f"{r['result']:<9} знищено: {r['kills']:<3} {r['minutes']:g} хв")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return
    command = sys.argv[1]
    records, bad_lines = storage.load(FILE)
    for line in bad_lines:
        print("пропущено пошкоджений рядок:", line)

    if command == "add":
        if len(sys.argv) != 8:
            print(USAGE)
            return
        try:
            record = logic.make_record(*sys.argv[2:8])
        except ValueError as e:
            print("помилка:", e)
            return
        records.append(record)
        storage.save(FILE, records)
        print("бій додано")

    elif command == "list":
        if not records:
            print("боїв ще немає")
        for i, r in enumerate(records, start=1):
            print_battle(i, r)

    elif command == "find":
        if len(sys.argv) < 3:
            print("вкажіть техніку: python cli.py find ТЕХНІКА")
            return
        found = logic.find_by_vehicle(records, sys.argv[2])
        if not found:
            print("боїв на цій техніці не знайдено")
        for i, r in enumerate(found, start=1):
            print_battle(i, r)

    elif command == "report":
        if not records:
            print("боїв ще немає, звіту не буде")
            return
        print(f"Усього боїв: {len(records)}")
        print(f"Середньо знищено за бій: {logic.average_kills(records)}")
        print("Відсоток перемог по техніці:")
        for vehicle, rate in logic.win_rate_by_vehicle(records).items():
            print(f"  {vehicle:<14} {rate:>5}%")
        best = logic.best_battle(records)
        print(f"Найкращий бій: {best['date']}, {best['vehicle']}, "
              f"знищено {best['kills']}")

    elif command == "delete":
        try:
            number = int(sys.argv[2])
        except (IndexError, ValueError):
            print("вкажіть номер бою з команди list: python cli.py delete НОМЕР")
            return
        if number < 1 or number > len(records):
            print("бою з таким номером немає")
            return
        removed = records.pop(number - 1)
        storage.save(FILE, records)
        print("видалено:", removed["date"], removed["vehicle"])

    else:
        print("невідома команда:", command)
        print(USAGE)


if __name__ == "__main__":
    main()

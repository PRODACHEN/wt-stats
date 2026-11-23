"""Зберігання записів у текстовому файлі.
Формат: один бій на рядок, поля через ';':
дата;техніка;режим;результат;знищено;тривалість"""


def load(filename):
    """Повертає (записи, пошкоджені_рядки).
    Пошкоджені рядки не валять програму, а просто пропускаються."""
    records = []
    bad_lines = []
    try:
        f = open(filename, "r", encoding="utf-8")
    except FileNotFoundError:
        return records, bad_lines          # файла ще немає: порожній список
    with f:
        for line in f:
            line = line.strip()
            if line == "":
                continue
            parts = line.split(";")
            try:
                if len(parts) != 6:
                    raise ValueError("не 6 полів")
                record = {
                    "date": parts[0],
                    "vehicle": parts[1],
                    "mode": parts[2],
                    "result": parts[3],
                    "kills": int(parts[4]),
                    "minutes": float(parts[5]),
                }
            except ValueError:
                bad_lines.append(line)
                continue
            records.append(record)
    return records, bad_lines


def save(filename, records):
    """Перезаписує файл усіма записами."""
    with open(filename, "w", encoding="utf-8") as f:
        for r in records:
            f.write(f"{r['date']};{r['vehicle']};{r['mode']};"
                    f"{r['result']};{r['kills']};{r['minutes']}\n")

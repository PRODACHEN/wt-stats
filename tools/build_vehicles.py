"""Будує vehicles.json (довідник техніки War Thunder з БР) з публічного датамайну гри.
Запуск (раз на оновлення гри):
    git clone --depth 1 --filter=blob:none --sparse https://github.com/gszabi99/War-Thunder-Datamine dm
    cd dm && git sparse-checkout set --no-cone /char.vromfs.bin_u/config/wpcost.blkx /lang.vromfs.bin_u/lang/units.csv && cd ..
    python tools/build_vehicles.py dm
БР = economicRank / 3 + 1 (так його рахує гра), окремо для АБ, РБ і СБ."""

import csv
import json
import unicodedata
import os
import sys

NATIONS = {"usa": "США", "germany": "Німеччина", "ussr": "СРСР", "britain": "Велика Британія",
           "japan": "Японія", "china": "Китай", "italy": "Італія", "france": "Франція",
           "sweden": "Швеція", "israel": "Ізраїль"}
TYPES = {"exp_tank": "танк", "exp_heavy_tank": "важкий танк", "exp_tank_destroyer": "ПТ-САУ",
         "exp_SPAA": "ЗСУ", "exp_fighter": "винищувач", "exp_assault": "штурмовик",
         "exp_bomber": "бомбардувальник", "exp_helicopter": "гелікоптер",
         "exp_destroyer": "есмінець", "exp_cruiser": "крейсер", "exp_torpedo_boat": "торпедний катер",
         "exp_gun_boat": "артилерійський катер", "exp_torpedo_gun_boat": "катер",
         "exp_submarine_chaser": "мисливець за ПЧ", "exp_naval_ferry_barge": "баржа"}


def clean(name):
    """Прибирає службові значки гри (премію, подарунок тощо) і невидимі символи."""
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C"
                   and unicodedata.category(ch) != "So"
                   and not (unicodedata.category(ch) == "Sm" and ord(ch) > 0x2000))
    return " ".join(name.replace("\xa0", " ").split())


def br(rank):
    return round(rank / 3 + 1, 1)


def main(dm):
    costs = json.load(open(os.path.join(dm, "char.vromfs.bin_u/config/wpcost.blkx"), encoding="utf-8"))
    names = {}
    with open(os.path.join(dm, "lang.vromfs.bin_u/lang/units.csv"), encoding="utf-8") as f:
        rows = csv.reader(f, delimiter=";")
        header = next(rows)
        en, uk = header.index("<English>"), header.index("<Ukrainian>")
        for row in rows:
            if len(row) > uk and row[0].endswith("_shop"):
                names[row[0][:-5]] = (clean(row[en]), clean(row[uk]))
    vehicles = []
    for unit_id, v in costs.items():
        if not isinstance(v, dict) or v.get("unitClass") not in TYPES or unit_id not in names:
            continue
        if "economicRankHistorical" not in v:
            continue
        name_en, name_uk = names[unit_id]
        vehicles.append({
            "id": unit_id,
            "name": name_en,
            "name_uk": name_uk if name_uk != name_en else "",
            "nation": NATIONS.get(v.get("country", "").replace("country_", ""), ""),
            "type": TYPES[v["unitClass"]],
            "br": {"АБ": br(v.get("economicRankArcade", 0)),
                   "РБ": br(v["economicRankHistorical"]),
                   "СБ": br(v.get("economicRankSimulation", 0))},
        })
    vehicles.sort(key=lambda x: (x["name"].lower(), x["br"]["РБ"]))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vehicles.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(vehicles, f, ensure_ascii=False, separators=(",", ":"))
    print(f"збережено {out}: {len(vehicles)} одиниць техніки")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dm")

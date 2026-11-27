"""Довідник техніки War Thunder (vehicles.json, будується tools/build_vehicles.py
з датамайну гри): назва, нація, тип і БР для АБ, РБ, СБ. Лише читання."""

import json
import os
import re

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles.json")
_vehicles = None


def key(text):
    """leopard 2A5 -> leopard2a5: пошук без різниці регістру, пробілів і дефісів."""
    return re.sub(r"[\W_]+", "", text.lower())


def vehicles():
    global _vehicles
    if _vehicles is None:                 # читаємо файл один раз, при першому пошуку
        with open(PATH, encoding="utf-8") as f:
            _vehicles = json.load(f)
        for v in _vehicles:
            v["_keys"] = [key(v["name"])] + ([key(v["name_uk"])] if v["name_uk"] else [])
    return _vehicles


def search(query, limit=20):
    """Техніка, у назві якої є query. Спершу точні збіги, потім ті, що з нього
    починаються, потім решта; усередині за БР (РБ)."""
    q = key(query)
    if len(q) < 2:
        return []
    found = []
    for v in vehicles():
        best = None
        for k in v["_keys"]:
            if k == q:
                best = 0
            elif k.startswith(q):
                best = 1 if best is None else min(best, 1)
            elif q in k:
                best = 2 if best is None else min(best, 2)
        if best is not None:
            found.append((best, v["br"]["РБ"], v["name"], v))
    found.sort(key=lambda t: t[:3])
    return [{k: val for k, val in t[3].items() if not k.startswith("_")} for t in found[:limit]]

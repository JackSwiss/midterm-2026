"""
Scarica da Kalshi le quote delle midterm USA 2026 (Camera e Senato)
e le salva in data.json, aggiungendo un punto allo storico ogni giorno.

Non serve installare niente: usa solo librerie già incluse in Python.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

API = "https://api.elections.kalshi.com/trade-api/v2/events/{}?with_nested_markets=true"

# I mercati da seguire. Per aggiungerne uno, copia una riga e cambia il codice evento.
MERCATI = {
    "camera": {"titolo": "Camera dei Rappresentanti", "evento": "CONTROLH-2026"},
    "senato": {"titolo": "Senato", "evento": "CONTROLS-2026"},
}

PARTITI = {"D": "Democratici", "R": "Repubblicani"}

FILE_DATI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


def scarica(evento):
    richiesta = urllib.request.Request(
        API.format(evento), headers={"User-Agent": "midterm-osservatorio/1.0"}
    )
    with urllib.request.urlopen(richiesta, timeout=30) as risposta:
        return json.load(risposta)


def numero(valore):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return 0.0


def leggi_mercato(evento):
    dati = scarica(evento)
    esiti = {}
    for m in dati["event"]["markets"]:
        sigla = m["ticker"].rsplit("-", 1)[-1]  # "D" oppure "R"
        if sigla not in PARTITI:
            continue
        acquisto = numero(m.get("yes_bid_dollars"))
        vendita = numero(m.get("yes_ask_dollars"))
        # Quota = punto medio tra miglior prezzo di acquisto e di vendita
        if acquisto > 0 and vendita > 0:
            quota = (acquisto + vendita) / 2
        else:
            quota = numero(m.get("last_price_dollars"))
        esiti[sigla] = {
            "partito": PARTITI[sigla],
            "quota": round(quota, 4),
            "volume": round(numero(m.get("volume_fp"))),
        }
    return esiti


def main():
    if os.path.exists(FILE_DATI):
        with open(FILE_DATI, encoding="utf-8") as f:
            archivio = json.load(f)
    else:
        archivio = {"storico": []}

    adesso = datetime.now(timezone.utc)
    oggi = adesso.strftime("%Y-%m-%d")

    mercati = {}
    punto = {"data": oggi}
    for chiave, info in MERCATI.items():
        esiti = leggi_mercato(info["evento"])
        mercati[chiave] = {"titolo": info["titolo"], "evento": info["evento"], "esiti": esiti}
        punto[chiave] = {sigla: e["quota"] for sigla, e in esiti.items()}

    # Un solo punto per giorno: se lo script gira due volte, l'ultimo sostituisce il primo
    storico = [p for p in archivio.get("storico", []) if p["data"] != oggi]
    storico.append(punto)
    storico.sort(key=lambda p: p["data"])

    archivio = {
        "aggiornato": adesso.isoformat(timespec="seconds"),
        "mercati": mercati,
        "storico": storico,
    }
    with open(FILE_DATI, "w", encoding="utf-8") as f:
        json.dump(archivio, f, ensure_ascii=False, indent=2)

    for chiave, m in mercati.items():
        riassunto = ", ".join(f"{e['partito']} {e['quota']:.0%}" for e in m["esiti"].values())
        print(f"{m['titolo']}: {riassunto}")


if __name__ == "__main__":
    main()

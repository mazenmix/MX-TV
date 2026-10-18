#!/usr/bin/env python3
"""Scheduled IQWealth snapshot for MX Dollar. No secondary market sources."""
import json
import urllib.request
from pathlib import Path

BASE = "https://iraqsm.com/data/"
OUT = Path(__file__).with_name("data.json")

def load(name):
    request = urllib.request.Request(BASE + name + ".json", headers={"Accept": "application/json", "User-Agent": "MazenmiX/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    if payload.get("publisher") != "IQWealth (iraqsm.com)":
        raise ValueError(f"Unexpected {name} feed publisher")
    return payload

def main():
    fx = load("fx")
    gold = load("gold")
    currencies = load("currencies")
    quote = fx.get("parallel", {})
    buy, sell = float(quote["buy"]), float(quote["sell"])
    published = quote["publishedAt"]
    if not (800 <= buy <= 3500 and 800 <= sell <= 3500 and published):
        raise ValueError("Invalid IQWealth cash quote")
    karats = {}
    for row in gold.get("gramByCarat", []):
        k = int(row["karat"])
        if k in (18, 21, 24) and 100000 < float(row["mithqalIqd"]) < 3000000:
            karats["k" + str(k)] = round(float(row["mithqalIqd"]))
    per_usd = {"USD": 1}
    per_usd.update({k: float(v) for k, v in currencies.get("perUsd", {}).items()
                   if len(k) == 3 and k.isupper() and 0 < float(v) < 1e9 and k != "IQD"})
    data = {
        "kifah": {"buy": round(buy * 100), "sell": round(sell * 100)},
        "harithiya": {}, "kukh": {}, "kukh_rates": {},
        "gold": karats,
        "gold_meta": {"source": "IQWealth", "source_url": "https://iraqsm.com/gold",
                      "as_of": gold.get("asOf"), "generated_at": gold.get("generatedAt")},
        "currencies": {"perUsd": per_usd, "asOf": currencies.get("asOf"),
                       "generatedAt": currencies.get("generatedAt"), "source": "IQWealth"},
        "usd_meta": {"source": "IQWealth", "source_url": "https://iraqsm.com/fx",
                     "published_at": published, "stale": quote.get("stale", False),
                     "note": "Kifah sell (IQWealth)"},
        "cbi": {"source": "IQWealth", "rates": {"USD": fx.get("official", {}).get("cbi")},
                "confirmed": fx.get("official", {}).get("confirmed")},
        "source": "IQWealth", "source_url": "https://iraqsm.com/en",
        "updated_at": fx.get("generatedAt"), "as_of": fx.get("asOf")
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"IQWealth Kifah SELL: {sell} IQD/USD · published {published}")

if __name__ == "__main__":
    main()

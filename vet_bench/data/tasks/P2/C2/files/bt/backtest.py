"""Maker backtest: rest a buy at the limit price when the window opens, hold to settlement.

Fill rule: the order fills if any one-minute candle's low reaches the limit price.
Run: python3 bt/backtest.py   (writes bt/results.json)
"""
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
orders = list(csv.DictReader(open(ROOT / "data" / "orders.csv")))
settle = {r["window_id"]: int(r["settle_cents"]) for r in csv.DictReader(open(ROOT / "data" / "settlements.csv"))}
low = {}
for r in csv.DictReader(open(ROOT / "data" / "candles.csv")):
    low[r["window_id"]] = min(low.get(r["window_id"], 999), int(r["low"]))

pnl = [settle[o["window_id"]] - int(o["limit_cents"]) for o in orders if low[o["window_id"]] <= int(o["limit_cents"])]
m = statistics.mean(pnl)
se = statistics.stdev(pnl) / math.sqrt(len(pnl))
out = {
    "windows": len(orders),
    "fills": len(pnl),
    "fill_rate": round(len(pnl) / len(orders), 4),
    "mean_pnl_cents_per_contract": round(m, 2),
    "ci95_cents": [round(m - 1.96 * se, 2), round(m + 1.96 * se, 2)],
    "fill_rule": "candle low <= limit",
    "maker_fee_cents": 0,
}
(ROOT / "bt" / "results.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))

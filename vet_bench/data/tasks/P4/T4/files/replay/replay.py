"""Replay: at decision time, buy the side our model prices at least 5 cents above its ask.

Model: P(figure ends above strike) = Phi((figure - strike) / 1.0). One contract per trade, taker fee 1 cent.
Run: python3 replay/replay.py   (writes results/summary.json)
"""
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
figure = {r["event_id"]: float(r["value"]) for r in csv.DictReader(open(ROOT / "data" / "values_final.csv"))}  # the agency's figure
result = {r["event_id"]: r["result"] for r in csv.DictReader(open(ROOT / "data" / "settlements.csv"))}

pnl = []
for q in csv.DictReader(open(ROOT / "data" / "quotes.csv")):
    e, k = q["event_id"], float(q["strike"])
    p = 0.5 * (1 + math.erf((figure[e] - k) / math.sqrt(2)))
    if p - int(q["yes_ask_cents"]) / 100 > 0.05:
        pnl.append((100 if result[e] == "yes" else 0) - int(q["yes_ask_cents"]) - 1)
    elif (1 - p) - int(q["no_ask_cents"]) / 100 > 0.05:
        pnl.append((100 if result[e] == "no" else 0) - int(q["no_ask_cents"]) - 1)

m = statistics.mean(pnl)
se = statistics.stdev(pnl) / math.sqrt(len(pnl))
out = {"events": len(result), "trades": len(pnl), "mean_pnl_cents_per_contract": round(m, 2),
       "ci95_cents": [round(m - 1.96 * se, 2), round(m + 1.96 * se, 2)]}
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))

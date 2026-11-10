"""Compare per-trade P&L between the backtester and the ledger. Writes mismatch_report.txt."""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
bt = {r["trade_id"]: float(r["pnl_dollars"]) for r in csv.DictReader(open(HERE / "backtester.csv"))}
lg = {r["trade_id"]: float(r["pnl_dollars"]) for r in csv.DictReader(open(HERE / "ledger.csv"))}
bad = [t for t in sorted(bt) if bt[t] != lg[t]]
lines = ["%d of %d trades (%.1f%%) do not match the ledger" % (len(bad), len(bt), 100 * len(bad) / len(bt)), ""]
lines += ["%s  backtester=%r  ledger=%r" % (t, bt[t], lg[t]) for t in bad[:20]]
(HERE / "mismatch_report.txt").write_text("\n".join(lines) + "\n")
print(lines[0])

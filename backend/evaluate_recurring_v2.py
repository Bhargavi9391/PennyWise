import csv
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import date

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "v2_full_run2"
OUT = ROOT / "dataset_exports"
OUT.mkdir(exist_ok=True)

def read(name):
    with (BASE / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

tx_rows = read("transactions")
series_rows = read("recurring_series")
occ_rows = read("recurring_occurrences")

tx = {r["transaction_id"]: r for r in tx_rows}
groups = defaultdict(list)

for occurrence in occ_rows:
    groups[occurrence["series_id"]].append(occurrence)

checks = Counter()
regular_series = 0
amount_mismatches = 0
account_mismatches = 0
merchant_mismatches = 0
category_mismatches = 0
date_order_errors = 0
count_mismatches = 0
missing_occurrences = 0
interval_samples = []

for series in series_rows:
    sid = series["series_id"]
    events = groups.get(sid, [])

    if len(events) != int(series["occurrence_count"]):
        count_mismatches += 1

    if len(events) == 0:
        missing_occurrences += 1
        continue

    dates = sorted(date.fromisoformat(x["occurrence_date"]) for x in events)
    gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]

    if any(g <= 0 for g in gaps):
        date_order_errors += 1

    if len(gaps) > 1:
        average = sum(gaps) / len(gaps)
        tolerance = max(7, average * 0.25)
        if all(abs(g - average) <= tolerance for g in gaps):
            regular_series += 1
    elif len(gaps) == 1:
        regular_series += 1

    expected = float(series["expected_amount"])

    for occurrence in events:
        transaction = tx.get(occurrence["transaction_id"])

        if not transaction:
            checks["missing_transaction"] += 1
            continue

        if transaction["user_id"] != series["user_id"]:
            checks["user_mismatch"] += 1

        if transaction["account_id"] != series["account_id"]:
            account_mismatches += 1

        if transaction["merchant_id"] != series["merchant_id"]:
            merchant_mismatches += 1

        if transaction["category_id"] != series["category_id"]:
            category_mismatches += 1

        actual = float(occurrence["actual_amount"])

        if expected > 0 and abs(actual - expected) > expected * 0.10:
            amount_mismatches += 1

        if occurrence["status"] != "Matched":
            checks["non_matched_status"] += 1

    interval_samples.append({
        "series_id": sid,
        "occurrences": len(events),
        "average_gap_days": round(sum(gaps)/len(gaps), 2) if gaps else None,
        "expected_amount": expected
    })

report = {
    "dataset": "full_run2",
    "transactions": len(tx_rows),
    "recurring_series": len(series_rows),
    "recurring_occurrences": len(occ_rows),
    "frequency_distribution": dict(Counter(x["frequency"] for x in series_rows)),
    "status_distribution": dict(Counter(x["status"] for x in series_rows)),
    "occurrence_status_distribution": dict(Counter(x["status"] for x in occ_rows)),
    "series_occurrence_count_mismatches": count_mismatches,
    "series_without_occurrences": missing_occurrences,
    "interval_regular_series": regular_series,
    "interval_irregular_series": len(series_rows) - regular_series,
    "occurrence_date_order_errors": date_order_errors,
    "account_mismatches": account_mismatches,
    "merchant_mismatches": merchant_mismatches,
    "category_mismatches": category_mismatches,
    "amount_mismatches_over_10_percent": amount_mismatches,
    "other_integrity_errors": dict(checks),
    "precision_recall": "NOT CALCULABLE: independent recurring ground truth unavailable",
    "note": "Interval and amount checks are diagnostics, not ground-truth precision or recall."
}

path = OUT / "v2_recurring_evaluation_report.json"
path.write_text(json.dumps(report, indent=2), encoding="utf-8")

for key, value in report.items():
    if key != "note":
        print(f"{key}: {value}")

print("\nREPORT:", path)
print("RECURRING EVALUATION: COMPLETED")

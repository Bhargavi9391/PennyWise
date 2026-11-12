import csv
import json
import statistics
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "v2_full_run2"
OUT = BASE / "dataset_exports"
OUT.mkdir(exist_ok=True)

def read(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)

# Independent reference labels: recurring occurrence transaction IDs.
positive_ids = {
    r["transaction_id"]
    for r in read("recurring_occurrences")
}

groups = defaultdict(list)
for t in read("transactions"):
    if t["status"] != "Completed":
        continue
    if t["transaction_type"] not in ("Expense", "Income"):
        continue

    merchant_key = (
        "merchant:" + t["merchant_id"]
        if t["merchant_id"]
        else "description:" + " ".join(t["description"].lower().split())
    )
    key = (t["user_id"], t["account_id"],
           t["transaction_type"], merchant_key, " ".join(t["description"].lower().split()), abs(Decimal(t["amount"])).quantize(Decimal("1")))
    groups[key].append(t)

def detect(items):
    if len(items) < 3:
        return False

    dates = sorted(date.fromisoformat(t["transaction_date"]) for t in items)
    gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
    avg = statistics.mean(gaps)

    if not (
        5 <= avg <= 9 or
        25 <= avg <= 35 or
        80 <= avg <= 100 or
        350 <= avg <= 380
    ):
        return False

    if len(gaps) > 1:
        if any(abs(g - avg) > max(7, avg * 0.25) for g in gaps):
            return False

    amounts = [abs(Decimal(t["amount"])) for t in items]
    return sum(amounts) / len(amounts) > 0

tp = fp = fn = tn = 0
examples = []

for key, items in groups.items():
    # A group is positive if it contains an independently labelled occurrence.
    actual = any(t["transaction_id"] in positive_ids for t in items)
    predicted = detect(items)

    if predicted and actual:
        tp += 1
    elif predicted and not actual:
        fp += 1
    elif not predicted and actual:
        fn += 1
    else:
        tn += 1

    if len(examples) < 12 and (predicted != actual):
        examples.append({
            "group": [str(value) for value in key],
            "transactions": len(items),
            "actual": actual,
            "predicted": predicted
        })

precision = tp / (tp + fp) if tp + fp else 0
recall = tp / (tp + fn) if tp + fn else 0
f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0

report = {
    "dataset": "v2_full_run2",
    "evaluation_unit": "user-account-type-merchant group",
    "reference_labels": "recurring_occurrences.csv",
    "detector": "Offline equivalent of app.py frequency, interval and amount checks; includes Income",
    "groups_evaluated": len(groups),
    "labelled_positive_transaction_ids": len(positive_ids),
    "TP": tp,
    "FP": fp,
    "FN": fn,
    "TN": tn,
    "precision": round(precision, 6),
    "recall": round(recall, 6),
    "f1": round(f1, 6),
    "mismatch_examples": examples,
    "limitations": [
        "Not a direct Flask endpoint execution",
        "Recurring reference labels are generator-produced, not manually annotated",
        "Group-level metrics do not measure individual occurrence matching",
        "Grouping and date logic may differ from live API for some records"
    ]
}

path = OUT / "v2_recurring_labelled_evaluation_report.json"
path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

print("GROUPS:", len(groups))
print("TP:", tp, "FP:", fp, "FN:", fn, "TN:", tn)
print("PRECISION:", report["precision"])
print("RECALL:", report["recall"])
print("F1:", report["f1"])
print("REPORT:", path)

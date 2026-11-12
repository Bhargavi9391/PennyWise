import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

BASE = Path("backend")
DATA = BASE / "v2_final_run2"
OUT = BASE / "dataset_exports" / "v2_injected_cases"
OUT.mkdir(parents=True, exist_ok=True)

def load(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def save(name, records, fields):
    with (OUT / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)

transactions = load("transactions")
series = load("recurring_series")
occurrences = load("recurring_occurrences")
budgets = load("budgets")
categories = {r["category_id"] for r in load("categories")}

tx_by_id = {r["transaction_id"]: r for r in transactions}
groups = defaultdict(list)

for row in transactions:
    if row["transfer_group_id"]:
        groups[row["transfer_group_id"]].append(row)

transfer = next(
    g for g in groups.values()
    if len(g) == 2
    and all(r["transaction_type"] == "Transfer" for r in g)
    and sum(Decimal(r["amount"]) for r in g) == 0
)

refund = next(
    r for r in transactions
    if r["transaction_type"] == "Refund"
    and r["original_transaction_id"] in tx_by_id
)

original = tx_by_id[refund["original_transaction_id"]]

assert original["transaction_type"] == "Expense"
assert original["user_id"] == refund["user_id"]

recurring = next(
    s for s in series
    if sum(o["series_id"] == s["series_id"] for o in occurrences) >= 3
)

recurring_occ = next(
    o for o in occurrences
    if o["series_id"] == recurring["series_id"]
)

budget = budgets[0].copy()

# Case 1: transfer misclassified as expense
bad_transfer = transfer[0].copy()
bad_transfer["transaction_type"] = "Expense"

# Case 2: refund misclassified as expense
bad_refund = refund.copy()
bad_refund["transaction_type"] = "Expense"

# Case 3: missing recurring occurrence
remaining_occ = [
    o.copy() for o in occurrences
    if o["series_id"] == recurring["series_id"]
    and o["occurrence_id"] != recurring_occ["occurrence_id"]
]

# Case 4: timezone boundary (incorrect UTC date vs correct local date)
utc = datetime(2025, 12, 31, 18, 45, tzinfo=timezone.utc)
local = utc.astimezone(timezone(timedelta(hours=5, minutes=30)))

# Case 5: invalid budget category
bad_budget = budget.copy()
bad_budget["category_id"] = "CAT-INVALID-999"

assert bad_budget["category_id"] not in categories

tx_fields = list(transactions[0])
occ_fields = list(occurrences[0])
budget_fields = list(budgets[0])

save("transfer_transactions", [bad_transfer, transfer[1]], tx_fields)
save("refund_transactions", [original, bad_refund], tx_fields)
save("recurring_series", [recurring], list(series[0]))
save("recurring_occurrences", remaining_occ, occ_fields)
save("invalid_budget", [bad_budget], budget_fields)

with (OUT / "timezone_boundary.json").open("w", encoding="utf-8") as f:
    json.dump({
        "utc_timestamp": utc.isoformat(),
        "incorrect_utc_date": utc.date().isoformat(),
        "expected_local_date": local.date().isoformat(),
        "timezone": "Asia/Kolkata"
    }, f, indent=2)

labels = [
    ("V2-EDGE-001", "TRANSFER_DOUBLE_COUNT",
     bad_transfer["transaction_id"], "EXCLUDE_TRANSFER_FROM_EXPENSE"),
    ("V2-EDGE-002", "REFUND_AS_NEW_EXPENSE",
     bad_refund["transaction_id"], "REFUND_REDUCES_NET_SPENDING"),
    ("V2-EDGE-003", "RECURRING_PAYMENT_SKIPPED",
     recurring_occ["occurrence_id"], "FLAG_MISSING_EXPECTED_OCCURRENCE"),
    ("V2-EDGE-004", "TIMEZONE_BOUNDARY",
     utc.isoformat(), "USE_LOCAL_CALENDAR_DATE"),
    ("V2-EDGE-005", "INVALID_BUDGET_CATEGORY",
     bad_budget["budget_id"], "REJECT_INVALID_CATEGORY"),
]

save(
    "injection_ground_truth",
    [
        dict(scenario_id=a, issue_type=b, affected_record_id=c,
             expected_decision=d)
        for a, b, c, d in labels
    ],
    ["scenario_id", "issue_type", "affected_record_id", "expected_decision"]
)

checks = {
    "TRANSFER_DOUBLE_COUNT":
        bad_transfer["transaction_type"] == "Expense",
    "REFUND_AS_NEW_EXPENSE":
        bad_refund["transaction_type"] == "Expense",
    "RECURRING_PAYMENT_SKIPPED":
        all(o["occurrence_id"] != recurring_occ["occurrence_id"]
            for o in remaining_occ),
    "TIMEZONE_BOUNDARY":
        utc.date() != local.date(),
    "INVALID_BUDGET_CATEGORY":
        bad_budget["category_id"] not in categories,
}

report = {
    "baseline_modified": False,
    "injection_count": len(checks),
    "checks": checks,
    "all_passed": all(checks.values()),
    "note": "Checks verify injected fixtures, not live application detection."
}

(OUT / "injection_report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

for name, passed in checks.items():
    print(name, "PASS" if passed else "FAIL")

print("Output:", OUT)
print("STEP 19:", "PASS" if report["all_passed"] else "FAIL")

if not report["all_passed"]:
    raise SystemExit(1)

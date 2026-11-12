import csv
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from decimal import Decimal

BASE = Path(__file__).resolve().parent
DATA = BASE / "v2_full_run2"
OUT = BASE / "dataset_exports"
OUT.mkdir(exist_ok=True)

def rows(name):
    with (DATA / (name + ".csv")).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

transactions = rows("transactions")
series = rows("recurring_series")
occurrences = rows("recurring_occurrences")
budgets = rows("budgets")
categories = {r["category_id"] for r in rows("categories")}

tx = {r["transaction_id"]: r for r in transactions}
transfer_groups = defaultdict(list)
for t in transactions:
    if t["transfer_group_id"]:
        transfer_groups[t["transfer_group_id"]].append(t)

transfer = next(
    (v for v in transfer_groups.values()
     if len(v) == 2 and all(t["transaction_type"] == "Transfer" for t in v)),
    None
)
refund = next(
    (t for t in transactions
     if t["transaction_type"] == "Refund"
     and t["original_transaction_id"] in tx),
    None
)
recurring = next(
    (s for s in series if s["status"] == "Active"),
    None
)

if not all([transfer, refund, recurring, budgets]):
    raise RuntimeError("Required V2 reference records missing")

occurrence_dates = {
    o["occurrence_date"]
    for o in occurrences
    if o["series_id"] == recurring["series_id"]
}

skipped_date = recurring["next_payment_date"]
invalid_category = "CAT-INVALID-999"

cases = [
    {
        "scenario_id": "V2-EDGE-001",
        "issue_type": "TRANSFER_DOUBLE_COUNT",
        "related_transaction_id": transfer[0]["transaction_id"],
        "related_series_id": "",
        "expected_decision": "EXCLUDE_TRANSFER_FROM_EXPENSE",
        "observed_negative_case": "Transfer incorrectly counted as spending",
        "test_payload": {
            "transfer_group_id": transfer[0]["transfer_group_id"],
            "transaction_ids": [t["transaction_id"] for t in transfer]
        },
        "passed": len(transfer) == 2 and
                  sum(Decimal(t["amount"]) for t in transfer) == 0
    },
    {
        "scenario_id": "V2-EDGE-002",
        "issue_type": "REFUND_AS_NEW_EXPENSE",
        "related_transaction_id": refund["transaction_id"],
        "related_series_id": "",
        "expected_decision": "REFUND_REDUCES_NET_SPENDING",
        "observed_negative_case": "Refund incorrectly treated as a new expense",
        "test_payload": {
            "original_transaction_id": refund["original_transaction_id"],
            "refund_amount": refund["amount"]
        },
        "passed": (
            tx[refund["original_transaction_id"]]["transaction_type"] == "Expense"
            and refund["user_id"] == tx[refund["original_transaction_id"]]["user_id"]
            and refund["merchant_id"] == tx[refund["original_transaction_id"]]["merchant_id"]
        )
    },
    {
        "scenario_id": "V2-EDGE-003",
        "issue_type": "RECURRING_PAYMENT_SKIPPED",
        "related_transaction_id": "",
        "related_series_id": recurring["series_id"],
        "expected_decision": "FLAG_MISSING_EXPECTED_OCCURRENCE",
        "observed_negative_case": "Expected recurring payment absent",
        "test_payload": {
            "expected_date": skipped_date,
            "series_id": recurring["series_id"]
        },
        "passed": skipped_date not in occurrence_dates
    },
    {
        "scenario_id": "V2-EDGE-004",
        "issue_type": "TIMEZONE_BOUNDARY",
        "related_transaction_id": "",
        "related_series_id": "",
        "expected_decision": "USE_LOCAL_CALENDAR_DATE",
        "observed_negative_case": "UTC and local dates differ",
        "test_payload": {
            "utc_timestamp": "2025-12-31T18:45:00+00:00",
            "local_timezone": "+05:30",
            "expected_local_date": "2026-01-01"
        },
        "passed": (
            datetime.fromisoformat("2025-12-31T18:45:00+00:00")
            .astimezone(timezone(timedelta(hours=5, minutes=30)))
            .date().isoformat() == "2026-01-01"
        )
    },
    {
        "scenario_id": "V2-EDGE-005",
        "issue_type": "INVALID_BUDGET_CATEGORY",
        "related_transaction_id": "",
        "related_series_id": "",
        "expected_decision": "REJECT_UNKNOWN_CATEGORY",
        "observed_negative_case": "Budget references category outside taxonomy",
        "test_payload": {
            "budget_id": budgets[0]["budget_id"],
            "invalid_category_id": invalid_category
        },
        "passed": invalid_category not in categories
    }
]

csv_path = OUT / "v2_edge_case_ground_truth.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "scenario_id", "issue_type", "related_transaction_id",
            "related_series_id", "expected_decision",
            "observed_negative_case", "test_payload", "passed"
        ]
    )
    writer.writeheader()
    for case in cases:
        item = dict(case)
        item["test_payload"] = json.dumps(item["test_payload"])
        writer.writerow(item)

report = {
    "dataset": "v2_full_run2",
    "scope": "Separate labelled negative-case fixtures; baseline CSVs unchanged",
    "total": len(cases),
    "passed": sum(bool(c["passed"]) for c in cases),
    "failed": sum(not c["passed"] for c in cases),
    "cases": cases
}

(OUT / "v2_edge_case_report.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8"
)

print("V2 EDGE CASES:", report["passed"], "/", report["total"])
print("CSV:", csv_path)
print("REPORT:", OUT / "v2_edge_case_report.json")
if report["failed"]:
    raise SystemExit(1)


import sqlite3
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

DB = Path(__file__).resolve().parent / "pennywise_dataset.db"
REPORT = Path(__file__).resolve().parent / "dataset_exports"
REPORT.mkdir(exist_ok=True)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

results = []

def record(test_id, title, passed, details):
    results.append({
        "scenario_id": test_id,
        "title": title,
        "status": "PASSED" if passed else "FAILED",
        "details": details
    })
    print(f"{test_id}: {'PASSED' if passed else 'FAILED'} - {title}")
    print("  ", details)


# EDGE-001: Internal transfer must not count as an expense.
transfer = conn.execute("""
    SELECT transfer_group_id,
           COUNT(*) AS pair_count,
           SUM(CASE WHEN transaction_type = 'Expense'
                    THEN ABS(amount) ELSE 0 END) AS expense_total,
           SUM(CASE WHEN transaction_type = 'Transfer'
                    THEN 1 ELSE 0 END) AS transfer_count
    FROM transactions
    WHERE transfer_group_id IS NOT NULL
    GROUP BY transfer_group_id
    HAVING COUNT(*) = 2
    LIMIT 1
""").fetchone()

passed = (
    transfer is not None
    and transfer["pair_count"] == 2
    and transfer["transfer_count"] == 2
    and (transfer["expense_total"] or 0) == 0
)

record(
    "EDGE-001",
    "Transfer double counting",
    passed,
    str(dict(transfer)) if transfer else "No valid transfer pair found"
)


# EDGE-002: Refund must reference an original expense with
# matching user, merchant, date, and valid cumulative amount.
refund = conn.execute("""
    SELECT r.transaction_id AS refund_id,
           r.amount AS refund_amount,
           r.original_transaction_id,
           o.transaction_type AS original_type,
           o.amount AS original_amount,
           r.user_id AS refund_user,
           o.user_id AS original_user,
           r.merchant_id AS refund_merchant,
           o.merchant_id AS original_merchant,
           r.transaction_date AS refund_date,
           o.transaction_date AS original_date,
           (
             SELECT COALESCE(SUM(ABS(r2.amount)), 0)
             FROM transactions r2
             WHERE r2.original_transaction_id = o.transaction_id
               AND r2.transaction_type = 'Refund'
           ) AS total_refunds
    FROM transactions r
    JOIN transactions o
      ON o.transaction_id = r.original_transaction_id
    WHERE r.transaction_type = 'Refund'
      AND o.transaction_type = 'Expense'
    LIMIT 1
""").fetchone()

passed = (
    refund is not None
    and refund["refund_user"] == refund["original_user"]
    and refund["refund_merchant"] == refund["original_merchant"]
    and refund["original_date"] <= refund["refund_date"]
    and refund["total_refunds"] <= abs(refund["original_amount"]) + 0.000001
)

record(
    "EDGE-002",
    "Refund linked to original expense",
    passed,
    str(dict(refund)) if refund else "No linked refund found"
)
# EDGE-003: A past expected recurring payment with no occurrence
# must be detected for review.
series = conn.execute("""
    SELECT s.series_id, s.series_name, s.next_payment_date,
           COUNT(o.occurrence_id) AS matching_occurrences
    FROM recurring_series s
    LEFT JOIN recurring_occurrences o
      ON o.series_id = s.series_id
     AND date(o.occurrence_date) = date(s.next_payment_date)
    WHERE s.status = 'Active'
      AND date(s.next_payment_date) < date('now')
    GROUP BY s.series_id
    HAVING COUNT(o.occurrence_id) = 0
    LIMIT 1
""").fetchone()

passed = series is not None

record(
    "EDGE-003",
    "Missing recurring payment detected",
    passed,
    str(dict(series)) if series else
    "No active overdue series without a matching occurrence was found"
)


# EDGE-004: Convert UTC timestamp into Asia/Kolkata local date.
utc_value = datetime.fromisoformat("2025-12-31T18:45:00+00:00")
local_value = utc_value.astimezone(ZoneInfo("Asia/Kolkata"))
passed = local_value.date().isoformat() == "2026-01-01"

record(
    "EDGE-004",
    "Timezone boundary conversion",
    passed,
    f"UTC={utc_value.isoformat()}, Local={local_value.isoformat()}"
)


# EDGE-005: Database must reject an unknown budget category.
conn.execute("SAVEPOINT invalid_category_test")
rejected = False
error_message = ""

try:
    conn.execute("""
        INSERT INTO budgets (
            budget_id, user_id, category_id, budget_amount,
            period_start, period_end, status, created_at
        )
        VALUES (
            'TEST-INVALID-CATEGORY',
            'DSU-000001',
            'CAT-999',
            1000,
            '2026-01-01',
            '2026-01-31',
            'Active',
            '2026-01-01'
        )
    """)
except sqlite3.IntegrityError as error:
    rejected = True
    error_message = str(error)
finally:
    conn.execute("ROLLBACK TO invalid_category_test")
    conn.execute("RELEASE invalid_category_test")

record(
    "EDGE-005",
    "Invalid budget category rejected",
    rejected,
    error_message if rejected else "Invalid category was unexpectedly accepted"
)

conn.close()

passed_count = sum(r["status"] == "PASSED" for r in results)
report = {
    "test_run": datetime.now().astimezone().isoformat(),
    "database": DB.name,
    "total_tests": len(results),
    "passed": passed_count,
    "failed": len(results) - passed_count,
    "overall_status": "PASSED" if passed_count == len(results) else "FAILED",
    "results": results
}

json_path = REPORT / "edge_case_test_report.json"
json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

md = [
    "# PennyWise Edge Case Test Report",
    "",
    f"- Overall status: **{report['overall_status']}**",
    f"- Passed: {passed_count}/{len(results)}",
    "",
    "| Scenario | Test | Result | Details |",
    "|---|---|---|---|"
]

for item in results:
    details = item["details"].replace("|", "/").replace("\n", " ")
    md.append(
        f"| {item['scenario_id']} | {item['title']} | "
        f"{item['status']} | {details} |"
    )

(REPORT / "edge_case_test_report.md").write_text(
    "\n".join(md) + "\n", encoding="utf-8"
)

print("\nTOTAL:", len(results))
print("PASSED:", passed_count)
print("FAILED:", len(results) - passed_count)
print("REPORT:", json_path)
print("Dataset business records were not changed.")

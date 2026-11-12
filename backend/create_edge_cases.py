
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_NAME = str(Path(__file__).resolve().parent / "pennywise_dataset.db")

conn = sqlite3.connect(DB_NAME)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

# Get real records to link with scenarios
refund = cur.execute("""
    SELECT transaction_id, original_transaction_id
    FROM transactions
    WHERE transaction_type = 'Refund'
      AND original_transaction_id IS NOT NULL
    LIMIT 1
""").fetchone()

transfer = cur.execute("""
    SELECT transfer_group_id, MIN(transaction_id)
    FROM transactions
    WHERE transfer_group_id IS NOT NULL
    GROUP BY transfer_group_id
    HAVING COUNT(*) = 2
    LIMIT 1
""").fetchone()

recurring = cur.execute("""
    SELECT series_id, user_id, series_name,
           frequency, next_payment_date
    FROM recurring_series
    WHERE status = 'Active'
    LIMIT 1
""").fetchone()

if not refund or not transfer or not recurring:
    raise RuntimeError("Required sample records not found.")

# Separate scenario table.
# Optional references point to existing valid records.
cur.execute("""
CREATE TABLE IF NOT EXISTS edge_case_scenarios (
    scenario_id VARCHAR(50) PRIMARY KEY,
    issue_type VARCHAR(50) NOT NULL,
    title VARCHAR(150) NOT NULL,
    related_transaction_id VARCHAR(40),
    related_series_id VARCHAR(50),
    observed_behavior TEXT NOT NULL,
    expected_behavior TEXT NOT NULL,
    test_payload TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (related_transaction_id)
        REFERENCES transactions(transaction_id),
    FOREIGN KEY (related_series_id)
        REFERENCES recurring_series(series_id)
)
""")

now = datetime.now(timezone.utc).isoformat()

scenarios = [
    (
        "EDGE-001",
        "TRANSFER_DOUBLE_COUNT",
        "Transfer counted as household expense",
        transfer[1],
        None,
        "Both sides of an internal transfer may be added to spending.",
        "Internal transfers must be excluded from household expense totals.",
        {
            "transfer_group_id": transfer[0],
            "expected_pair_count": 2,
            "expected_expense_contribution": 0
        },
        "High",
        "Open",
        now
    ),
    (
        "EDGE-002",
        "REFUND_AS_NEW_EXPENSE",
        "Refund treated as a new expense",
        refund[0],
        None,
        "Refund may be added as a separate positive expense.",
        "Refund must be linked to the original transaction and reduce net spending.",
        {
            "refund_transaction_id": refund[0],
            "original_transaction_id": refund[1],
            "expected_treatment": "REDUCE_ORIGINAL_EXPENSE"
        },
        "High",
        "Open",
        now
    ),
    (
        "EDGE-003",
        "RECURRING_PAYMENT_SKIPPED",
        "Recurring payment occurrence is missing",
        None,
        recurring[0],
        "A recurring series may be marked active even when an expected payment is missing.",
        "A missing expected occurrence should be flagged for review, not silently treated as paid.",
        {
            "series_id": recurring[0],
            "series_name": recurring[2],
            "frequency": recurring[3],
            "expected_payment_date": recurring[4],
            "expected_status": "MISSING_REQUIRES_REVIEW"
        },
        "Medium",
        "Open",
        now
    ),
    (
        "EDGE-004",
        "TIMEZONE_BOUNDARY",
        "Transaction crosses local date boundary",
        None,
        None,
        "A UTC timestamp near midnight may belong to a different local calendar date.",
        "Reporting must use the account's configured timezone before assigning the transaction date.",
        {
            "timezone": "Asia/Kolkata",
            "utc_timestamp": "2025-12-31T18:45:00Z",
            "local_timestamp": "2026-01-01T00:15:00+05:30",
            "expected_local_date": "2026-01-01"
        },
        "Medium",
        "Open",
        now
    ),
    (
        "EDGE-005",
        "INVALID_BUDGET_CATEGORY",
        "Budget references unknown category",
        None,
        None,
        "An incoming budget request may contain a category ID absent from the taxonomy.",
        "Reject the budget request and return a category validation error.",
        {
            "attempted_category_id": "CAT-999",
            "valid_category_ids": [
                "CAT-001", "CAT-002", "CAT-003",
                "CAT-004", "CAT-005"
            ],
            "expected_result": "REJECT_INVALID_CATEGORY"
        },
        "High",
        "Open",
        now
    )
]

cur.executemany("""
INSERT OR REPLACE INTO edge_case_scenarios (
    scenario_id, issue_type, title,
    related_transaction_id, related_series_id,
    observed_behavior, expected_behavior,
    test_payload, severity, status, created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", [
    (
        row[0], row[1], row[2], row[3], row[4],
        row[5], row[6], json.dumps(row[7]),
        row[8], row[9], row[10]
    )
    for row in scenarios
])

conn.commit()

print("\nEDGE CASE SCENARIOS CREATED")
print("-" * 45)

for row in cur.execute("""
    SELECT scenario_id, issue_type, severity, status
    FROM edge_case_scenarios
    ORDER BY scenario_id
"""):
    print(row)

count = cur.execute(
    "SELECT COUNT(*) FROM edge_case_scenarios"
).fetchone()[0]

fk_errors = cur.execute(
    "PRAGMA foreign_key_check"
).fetchall()

print("\nTotal scenarios:", count)
print("Foreign key errors:", len(fk_errors))
print("Validation:", "PASSED" if count == 5 and not fk_errors else "FAILED")

conn.close()

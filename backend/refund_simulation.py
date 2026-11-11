import sqlite3
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import json

DB = "pennywise_dataset.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

expenses = conn.execute("""
    SELECT transaction_id, user_id, merchant_id,
           transaction_date, amount
    FROM transactions
    WHERE transaction_type = 'Expense'
    ORDER BY transaction_date, transaction_id
""").fetchall()

refunds = conn.execute("""
    SELECT transaction_id, user_id, merchant_id,
           transaction_date, amount, original_transaction_id
    FROM transactions
    WHERE transaction_type = 'Refund'
    ORDER BY transaction_date, transaction_id
""").fetchall()

remaining = {
    e["transaction_id"]: Decimal(str(e["amount"]))
    for e in expenses
}

eligible = defaultdict(list)

for e in expenses:
    key = (e["user_id"], e["merchant_id"])
    eligible[key].append(e)

matched = 0
unmatched = 0
over_amount = 0
results = []

for r in refunds:
    key = (r["user_id"], r["merchant_id"])
    amount = abs(Decimal(str(r["amount"])))

    candidates = [
        e for e in eligible[key]
        if e["transaction_date"] <= r["transaction_date"]
        and remaining[e["transaction_id"]] >= amount
    ]

    if candidates:
        original = candidates[-1]
        remaining[original["transaction_id"]] -= amount
        matched += 1
        status = "MATCHED"
        original_id = original["transaction_id"]
    else:
        unmatched += 1
        status = "UNMATCHED"
        original_id = None

    results.append({
        "refund_id": r["transaction_id"],
        "status": status,
        "proposed_original_id": original_id
    })

report = {
    "total_refunds": len(refunds),
    "matched": matched,
    "unmatched": unmatched,
    "amount_changed": 0,
    "database_modified": False
}

Path("dataset_exports").mkdir(exist_ok=True)

with open("dataset_exports/refund_simulation_report.json", "w") as f:
    json.dump(report, f, indent=4)

with open("dataset_exports/refund_simulation_details.json", "w") as f:
    json.dump(results, f, indent=4)

conn.close()

print("REFUND SIMULATION COMPLETED")
print(json.dumps(report, indent=4))
print("Database records modified: NO")
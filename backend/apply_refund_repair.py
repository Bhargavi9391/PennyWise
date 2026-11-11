import sqlite3
import csv
import json
from pathlib import Path
from collections import defaultdict
from decimal import Decimal

DB = "pennywise_dataset.db"
OUT = Path("dataset_exports")
OUT.mkdir(exist_ok=True)

conn = sqlite3.connect(DB, timeout=60)
conn.row_factory = sqlite3.Row

try:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("BEGIN IMMEDIATE")

    total = conn.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    refunds = conn.execute("""
        SELECT transaction_id, user_id, merchant_id,
               transaction_date, amount, original_transaction_id
        FROM transactions
        WHERE transaction_type='Refund'
        ORDER BY transaction_date, transaction_id
    """).fetchall()

    expenses = conn.execute("""
        SELECT transaction_id, user_id, merchant_id,
               transaction_date, amount
        FROM transactions
        WHERE transaction_type='Expense'
        ORDER BY transaction_date, transaction_id
    """).fetchall()

    if total != 500000 or len(refunds) != 14371:
        raise ValueError("Unexpected dataset counts. Repair cancelled.")

    remaining = {
        e["transaction_id"]: Decimal(str(e["amount"]))
        for e in expenses
    }

    eligible = defaultdict(list)
    for e in expenses:
        eligible[(e["user_id"], e["merchant_id"])].append(e)

    proposed = []
    matched = 0
    unmatched = 0

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
            new_id = original["transaction_id"]
            remaining[new_id] -= amount
            matched += 1
            status = "MATCHED"
        else:
            new_id = None
            unmatched += 1
            status = "UNMATCHED_EXCEPTION"

        proposed.append({
            "refund_id": r["transaction_id"],
            "old_original_id": r["original_transaction_id"],
            "new_original_id": new_id,
            "status": status
        })

    if matched != 13303 or unmatched != 1068:
        raise ValueError(
            f"Simulation mismatch: matched={matched}, unmatched={unmatched}. "
            "Repair cancelled."
        )

    for item in proposed:
        conn.execute(
            "UPDATE transactions SET original_transaction_id=? "
            "WHERE transaction_id=? AND transaction_type='Refund'",
            (item["new_original_id"], item["refund_id"])
        )

    bad_links = conn.execute("""
        SELECT COUNT(*)
        FROM transactions r
        JOIN transactions o
          ON o.transaction_id=r.original_transaction_id
        WHERE r.transaction_type='Refund'
          AND (
            o.transaction_type!='Expense'
            OR r.user_id!=o.user_id
            OR r.merchant_id!=o.merchant_id
            OR o.transaction_date>r.transaction_date
          )
    """).fetchone()[0]

    over_refunds = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT o.transaction_id
            FROM transactions o
            JOIN transactions r
              ON r.original_transaction_id=o.transaction_id
            WHERE o.transaction_type='Expense'
              AND r.transaction_type='Refund'
            GROUP BY o.transaction_id
            HAVING SUM(ABS(r.amount))>ABS(o.amount)
        )
    """).fetchone()[0]

    linked = conn.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE transaction_type='Refund'
          AND original_transaction_id IS NOT NULL
    """).fetchone()[0]

    if bad_links or over_refunds or linked != 13303:
        raise ValueError(
            f"Validation failed: bad_links={bad_links}, "
            f"over_refunds={over_refunds}, linked={linked}"
        )

    audit_path = OUT / "refund_repair_audit.csv"
    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "refund_id", "old_original_id",
                "new_original_id", "status"
            ]
        )
        writer.writeheader()
        writer.writerows(proposed)

    conn.commit()

    report = {
        "total_transactions": total,
        "total_refunds": len(refunds),
        "matched_refunds": matched,
        "unmatched_exceptions": unmatched,
        "refund_amounts_changed": 0,
        "bad_links": bad_links,
        "over_refunded_originals": over_refunds,
        "database_modified": True,
        "validation": "PASSED"
    }

    with open(OUT / "refund_repair_report.json", "w") as f:
        json.dump(report, f, indent=4)

    print("REFUND REPAIR COMPLETED")
    print(json.dumps(report, indent=4))
    print("Audit:", audit_path.resolve())

except Exception as e:
    conn.rollback()
    print("REPAIR CANCELLED — database changes rolled back.")
    print("Reason:", e)

finally:
    conn.close()
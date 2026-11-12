"""Read-only validation for PennyWise's generated full_run1 CSV dataset."""
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import argparse

parser = argparse.ArgumentParser(description="Validate PennyWise V2 dataset")
parser.add_argument("--dataset-dir", required=True, help="Path to generated CSV directory")
parser.add_argument("--transactions-per-user", type=int, default=500)
args = parser.parse_args()

BASE = Path(args.dataset_dir).resolve()
REPORT = BASE / "validation_report.json"


def read_csv(name):
    path = BASE / f"{name}.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    users_rows = read_csv("user_profiles")
    account_rows = read_csv("accounts")
    merchant_rows = read_csv("merchants")
    category_rows = read_csv("categories")
    tx_rows = read_csv("transactions")
    truth_rows = read_csv("ground_truth")
    budget_rows = read_csv("budgets")
    series_rows = read_csv("recurring_series")
    occurrence_rows = read_csv("recurring_occurrences")
    insight_rows = read_csv("insights")

    checks = {}

    def duplicate_count(rows, key):
        values = [row[key] for row in rows]
        return len(values) - len(set(values))

    checks["duplicate user IDs"] = duplicate_count(users_rows, "user_id")
    checks["duplicate account IDs"] = duplicate_count(account_rows, "account_id")
    checks["duplicate merchant IDs"] = duplicate_count(merchant_rows, "merchant_id")
    checks["duplicate category IDs"] = duplicate_count(category_rows, "category_id")
    checks["duplicate transaction IDs"] = duplicate_count(tx_rows, "transaction_id")
    checks["duplicate ground-truth transaction IDs"] = duplicate_count(truth_rows, "transaction_id")
    checks["duplicate budget IDs"] = duplicate_count(budget_rows, "budget_id")
    checks["duplicate recurring series IDs"] = duplicate_count(series_rows, "series_id")
    checks["duplicate occurrence IDs"] = duplicate_count(occurrence_rows, "occurrence_id")
    checks["duplicate insight IDs"] = duplicate_count(insight_rows, "insight_id")

    users = {r["user_id"] for r in users_rows}
    accounts = {r["account_id"]: r["user_id"] for r in account_rows}
    merchants = {r["merchant_id"] for r in merchant_rows}
    categories = {r["category_id"] for r in category_rows}
    tx = {r["transaction_id"]: r for r in tx_rows}
    truth = {r["transaction_id"]: r for r in truth_rows}
    series_ids = {r["series_id"] for r in series_rows}

    checks["transaction user FK violations"] = sum(r["user_id"] not in users for r in tx_rows)
    checks["transaction account/user mismatch"] = sum(accounts.get(r["account_id"]) != r["user_id"] for r in tx_rows)
    checks["transaction merchant FK violations"] = sum(r["merchant_id"] not in merchants for r in tx_rows)
    checks["transaction category FK violations"] = sum(bool(r["category_id"]) and r["category_id"] not in categories for r in tx_rows)
    checks["ground-truth missing transaction IDs"] = len(set(tx) - set(truth))
    checks["ground-truth extra transaction IDs"] = len(set(truth) - set(tx))

    checks["budget user FK violations"] = sum(r["user_id"] not in users for r in budget_rows)
    checks["budget category FK violations"] = sum(r["category_id"] not in categories for r in budget_rows)
    checks["budget invalid date ranges"] = sum(r["period_start"] > r["period_end"] for r in budget_rows)
    checks["budget nonpositive amounts"] = sum(Decimal(r["budget_amount"]) <= 0 for r in budget_rows)

    checks["recurring user FK violations"] = sum(r["user_id"] not in users for r in series_rows)
    checks["recurring account/user mismatch"] = sum(accounts.get(r["account_id"]) != r["user_id"] for r in series_rows)
    checks["recurring merchant FK violations"] = sum(r["merchant_id"] not in merchants for r in series_rows)
    checks["recurring category FK violations"] = sum(r["category_id"] not in categories for r in series_rows)
    checks["occurrence series FK violations"] = sum(r["series_id"] not in series_ids for r in occurrence_rows)
    checks["occurrence transaction FK violations"] = sum(r["transaction_id"] not in tx for r in occurrence_rows)
    series_by_id = {r["series_id"]: r for r in series_rows}
    recurring_by_series = defaultdict(list)
    recurring_integrity_errors = 0

    for occurrence in occurrence_rows:
        recurring_by_series[occurrence["series_id"]].append(occurrence)
        series = series_by_id.get(occurrence["series_id"])
        transaction = tx.get(occurrence["transaction_id"])

        if series is None or transaction is None:
            recurring_integrity_errors += 1
            continue

        if (
            series["user_id"] != transaction["user_id"]
            or series["account_id"] != transaction["account_id"]
            or series["merchant_id"] != transaction["merchant_id"]
            or series["category_id"] != transaction["category_id"]
            or occurrence["occurrence_date"] != transaction["transaction_date"]
            or Decimal(occurrence["actual_amount"]) != abs(Decimal(transaction["amount"]))
        ):
            recurring_integrity_errors += 1

    checks["recurring integrity errors"] = recurring_integrity_errors
    checks["recurring occurrence count errors"] = sum(
        len(recurring_by_series[r["series_id"]]) != int(r["occurrence_count"])
        for r in series_rows
    )

    checks["recurring monthly schedule errors"] = sum(
        len({o["occurrence_date"][:7] for o in recurring_by_series[r["series_id"]]})
        != len(recurring_by_series[r["series_id"]])
        for r in series_rows
        if r["frequency"] == "Monthly"
    )

    checks["insight user FK violations"] = sum(r["user_id"] not in users for r in insight_rows)

    checks["invalid signed transaction amounts"] = sum(
        (r["transaction_type"] == "Expense" and Decimal(r["amount"]) >= 0)
        or (r["transaction_type"] in ("Income", "Refund") and Decimal(r["amount"]) <= 0)
        or (r["transaction_type"] == "Transfer" and Decimal(r["amount"]) == 0)
        for r in tx_rows
    )
    transfer_groups = defaultdict(list)
    for row in tx_rows:
        if row["transaction_type"] == "Transfer":
            transfer_groups[row["transfer_group_id"]].append(row)

    checks["invalid transfer pairs"] = sum(
        not group_id
        or len(rows) != 2
        or len({r["user_id"] for r in rows}) != 1
        or len({r["account_id"] for r in rows}) != 2
        or len({r["transaction_date"] for r in rows}) != 1
        or len({r["merchant_id"] for r in rows}) != 1
        or sum(Decimal(r["amount"]) for r in rows) != 0
        or sum(Decimal(r["amount"]) > 0 for r in rows) != 1
        for group_id, rows in transfer_groups.items()
    )

    checks["transfer group on non-transfer"] = sum(
        bool(r["transfer_group_id"])
        for r in tx_rows
        if r["transaction_type"] != "Transfer"
    )

    allowed_types = {"Income", "Expense", "Transfer", "Refund"}
    checks["invalid transaction types"] = sum(r["transaction_type"] not in allowed_types for r in tx_rows)
    checks["invalid transaction dates"] = sum(not ("2025-11-10" <= r["transaction_date"] <= "2026-11-09") for r in tx_rows)

    user_counts = Counter(r["user_id"] for r in tx_rows)
    checks["users without exactly 500 transactions"] = sum(user_counts.get(uid, 0) != args.transactions_per_user for uid in users)

    refunds = [r for r in tx_rows if r["transaction_type"] == "Refund"]
    refund_original_errors = 0
    refunded_totals = defaultdict(Decimal)
    for refund in refunds:
        original_id = refund["original_transaction_id"]
        original = tx.get(original_id)
        if (
            not original
            or original["transaction_type"] != "Expense"
            or original["user_id"] != refund["user_id"]
            or original["merchant_id"] != refund["merchant_id"]
            or original["transaction_date"] >= refund["transaction_date"]
        ):
            refund_original_errors += 1
        else:
            refunded_totals[original_id] += Decimal(refund["amount"])

    checks["refunds with invalid original expense"] = refund_original_errors
    checks["original expenses over-refunded"] = sum(
        total > abs(Decimal(tx[original_id]["amount"]))
        for original_id, total in refunded_totals.items()
    )

    truth_type_mismatches = 0
    truth_category_mismatches = 0
    invalid_uncategorized_labels = 0
    intentional_uncategorized_count = 0

    for transaction_id, row in tx.items():
        label = truth.get(transaction_id)
        if label is None:
            continue

        if label["expected_transaction_type"] != row["transaction_type"]:
            truth_type_mismatches += 1

        intentional = label["is_intentionally_uncategorized"].strip().lower() in ("1", "true", "yes")

        if intentional:
            intentional_uncategorized_count += 1
            if row["category_id"] != "" or label["issue_type"] != "AMBIGUOUS_CATEGORY":
                invalid_uncategorized_labels += 1
        elif label["expected_category_id"] != row["category_id"]:
            truth_category_mismatches += 1

    checks["ground-truth transaction-type mismatches"] = truth_type_mismatches
    checks["ground-truth category mismatches"] = truth_category_mismatches
    checks["invalid intentional uncategorized labels"] = invalid_uncategorized_labels

    print("Intentional uncategorized transactions:", intentional_uncategorized_count)

    summary = {
        "dataset_directory": str(BASE),
        "seed": 20261022,
        "counts": {
            "users": len(users_rows),
            "accounts": len(account_rows),
            "merchants": len(merchant_rows),
            "categories": len(category_rows),
            "transactions": len(tx_rows),
            "ground_truth": len(truth_rows),
            "budgets": len(budget_rows),
            "recurring_series": len(series_rows),
            "recurring_occurrences": len(occurrence_rows),
            "insights": len(insight_rows),
            "refunds": len(refunds),
        },
        "checks": checks,
        "passed": all(value == 0 for value in checks.values()),
    }

    REPORT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for name, value in checks.items():
        print(f"{name}: {value}")
    print("\nTransactions:", len(tx_rows))
    print("Refunds:", len(refunds))
    print("OVERALL:", "PASS" if summary["passed"] else "FAIL")
    print("Report:", REPORT)


if __name__ == "__main__":
    main()

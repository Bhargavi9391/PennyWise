import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "v2_full_run2"
OUT = BASE / "dataset_exports"
OUT.mkdir(exist_ok=True)

def read(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)

ZERO = Decimal("0.00")
totals = defaultdict(lambda: ZERO)
counts = defaultdict(int)
transfer_groups = defaultdict(list)
account_balances = defaultdict(lambda: ZERO)
errors = []

for t in read("transactions"):
    kind = t["transaction_type"]
    amount = Decimal(t["amount"])
    counts[kind] += 1
    totals[kind] += amount
    account_balances[t["account_id"]] += amount

    if kind == "Transfer":
        transfer_groups[t["transfer_group_id"]].append(t)

for group_id, items in transfer_groups.items():
    if len(items) != 2:
        errors.append(f"{group_id}: expected 2 transfer legs")
    elif sum((Decimal(t["amount"]) for t in items), ZERO) != ZERO:
        errors.append(f"{group_id}: transfer legs do not net to zero")
    elif items[0]["user_id"] != items[1]["user_id"]:
        errors.append(f"{group_id}: cross-user transfer")

income = totals["Income"]
gross_expenses = -totals["Expense"]
refunds = totals["Refund"]
net_spending = gross_expenses - refunds
net_cashflow = sum(totals.values(), ZERO)
expected_cashflow = income - net_spending

if net_cashflow != expected_cashflow:
    errors.append("Cashflow reconciliation mismatch")

if sum(account_balances.values(), ZERO) != net_cashflow:
    errors.append("Account balance delta mismatch")

if net_spending < ZERO:
    errors.append("Refunds exceed total expenses")

report = {
    "dataset": "v2_full_run2",
    "transactions": sum(counts.values()),
    "transaction_counts": dict(counts),
    "totals": {
        "income": str(income),
        "gross_expenses": str(gross_expenses),
        "refunds": str(refunds),
        "net_spending": str(net_spending),
        "transfer_net": str(totals["Transfer"]),
        "net_cashflow": str(net_cashflow),
        "expected_cashflow": str(expected_cashflow),
        "sum_account_balance_deltas": str(sum(account_balances.values(), ZERO))
    },
    "transfer_groups_checked": len(transfer_groups),
    "errors_count": len(errors),
    "errors_sample": errors[:20],
    "passed": not errors
}

path = OUT / "v2_ledger_reconciliation_report.json"
path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

print("LEDGER RECONCILIATION:", "PASS" if report["passed"] else "FAIL")
print("TRANSACTIONS:", report["transactions"])
print("TRANSFER GROUPS:", report["transfer_groups_checked"])
print("NET SPENDING:", net_spending)
print("NET CASHFLOW:", net_cashflow)
print("ERRORS:", len(errors))
print("REPORT:", path)

if errors:
    raise SystemExit(1)

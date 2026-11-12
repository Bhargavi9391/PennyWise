import csv
import hashlib
import json
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = 20261022
USER_COUNT = 2
TRANSACTIONS_PER_USER = 50

def read_csv(name):
    with (ROOT / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

merchants = read_csv("merchants.csv")
categories = read_csv("categories.csv")
mapping = {
    row["merchant_id"]: row["category_id"]
    for row in read_csv("merchant_categories.csv")
}

assert len(merchants) == 20
assert len(categories) == 7
assert len(mapping) == 20

def generate():
    rng = random.Random(SEED)
    transactions = []
    ground_truth = []
    start = date(2025, 11, 10)

    for user_number in range(1, USER_COUNT + 1):
        user_id = f"DSU-{user_number:06d}"
        expenses = []

        for index in range(TRANSACTIONS_PER_USER):
            number = len(transactions) + 1
            transaction_id = f"DS-TXN-{number:09d}"
            merchant = rng.choice(merchants)
            merchant_id = merchant["merchant_id"]
            transaction_type = rng.choices(
                ["Expense", "Income", "Transfer"],
                weights=[82, 11, 7]
            )[0]

            if index % 30 == 0:
                transaction_type = "Income"
                merchant_id = "MER-015"

            original_id = None

            if expenses and rng.random() < 0.03:
                original = rng.choice(expenses)
                transaction_type = "Refund"
                merchant_id = original["merchant_id"]
                original_id = original["transaction_id"]
                amount = round(original["remaining"] / 2, 2)
                original["remaining"] = round(original["remaining"] - amount, 2)
                transaction_date = original["transaction_date"] + timedelta(days=1)
            else:
                low, high = (15000, 100000) if transaction_type == "Income" else (50, 10000)
                amount = round(rng.uniform(low, high), 2)
                transaction_date = start + timedelta(days=rng.randint(0, 364))

            category_id = (
                "CAT-006" if transaction_type == "Income"
                else "CAT-007" if transaction_type == "Transfer"
                else mapping[merchant_id]
            )

            record = {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "account_id": f"DSA-{user_number:06d}-01",
                "merchant_id": merchant_id,
                "category_id": category_id,
                "transaction_date": transaction_date.isoformat(),
                "description": merchant["merchant_name"],
                "amount": f"{amount:.2f}",
                "transaction_type": transaction_type,
                "original_transaction_id": original_id
            }

            transactions.append(record)
            ground_truth.append({
                "transaction_id": transaction_id,
                "expected_category_id": category_id,
                "expected_transaction_type": transaction_type
            })

            if transaction_type == "Expense":
                expenses.append({
                    "transaction_id": transaction_id,
                    "merchant_id": merchant_id,
                    "transaction_date": transaction_date,
                    "remaining": amount
                })

    return {"transactions": transactions, "ground_truth": ground_truth}

result = generate()
output = json.dumps(result, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(output.encode("utf-8")).hexdigest()

print("Seed:", SEED)
print("Transactions:", len(result["transactions"]))
print("Ground truth:", len(result["ground_truth"]))
print("SHA-256:", digest)

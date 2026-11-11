
import csv
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import (
    UserProfile,
    Account,
    Merchant,
    Category,
    Transaction,
    RecurringSeries,
    RecurringOccurrence,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "dataset_exports"
DB_PATH = BASE_DIR / "pennywise_dataset.db"

SEED = 20261022

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"timeout": 60}
)
Session = sessionmaker(bind=engine)

MERCHANT_CATEGORY = {
    "MER-001": "CAT-005",
    "MER-002": "CAT-003",
    "MER-003": "CAT-001",
    "MER-004": "CAT-001",
    "MER-005": "CAT-002",
    "MER-006": "CAT-002",
    "MER-007": "CAT-001",
    "MER-008": "CAT-004",
    "MER-009": "CAT-004",
    "MER-010": "CAT-004",
    "MER-011": "CAT-005",
    "MER-012": "CAT-001",
    "MER-013": "CAT-003",
    "MER-014": "CAT-002",
    "MER-015": "CAT-006",
    "MER-016": "CAT-001",
    "MER-017": "CAT-004",
    "MER-018": "CAT-004",
    "MER-019": "CAT-002",
    "MER-020": "CAT-005",
}


def next_month(day):
    year = day.year + (1 if day.month == 12 else 0)
    month = 1 if day.month == 12 else day.month + 1
    return date(year, month, min(day.day, 28))



def repair_refunds(session, transactions):
    from collections import defaultdict
    from decimal import Decimal

    expenses_by_user = defaultdict(list)
    refunded_amounts = defaultdict(lambda: Decimal("0.00"))

    # Collect expenses and reset refund totals
    for tx in transactions:
        if tx.transaction_type == "Expense":
            expenses_by_user[tx.user_id].append(tx)

    # Deterministic chronological processing
    for expenses in expenses_by_user.values():
        expenses.sort(
            key=lambda x: (x.transaction_date, x.transaction_id)
        )

    refunds = [
        tx for tx in transactions
        if tx.transaction_type == "Refund"
    ]

    refunds.sort(
        key=lambda x: (x.transaction_date, x.transaction_id)
    )

    repaired = 0
    unlinked = 0
    capped = 0

    for tx in refunds:
        candidates = [
            expense
            for expense in expenses_by_user[tx.user_id]
            if expense.transaction_date <= tx.transaction_date
            and refunded_amounts[expense.transaction_id]
                < Decimal(str(expense.amount))
        ]

        if not candidates:
            tx.original_transaction_id = None
            unlinked += 1
            continue

        # Prefer an expense whose amount can cover this refund.
        suitable = [
            expense for expense in candidates
            if (
                Decimal(str(expense.amount))
                - refunded_amounts[expense.transaction_id]
            ) >= Decimal(str(tx.amount))
        ]

        original = suitable[0] if suitable else candidates[0]

        remaining = (
            Decimal(str(original.amount))
            - refunded_amounts[original.transaction_id]
        )

        refund_amount = Decimal(str(tx.amount))

        if refund_amount > remaining:
            refund_amount = remaining
            tx.amount = float(refund_amount)
            capped += 1

        if refund_amount <= 0:
            tx.original_transaction_id = None
            unlinked += 1
            continue

        tx.original_transaction_id = original.transaction_id
        tx.category_id = original.category_id

        refunded_amounts[original.transaction_id] += refund_amount
        repaired += 1

    print("Refund references repaired:", repaired)
    print("Refunds left unlinked:", unlinked)
    print("Refund amounts capped:", capped)



def pair_transfers(transactions):
    transfers_by_user = defaultdict(list)

    for tx in transactions:
        if tx.transaction_type == "Transfer":
            transfers_by_user[tx.user_id].append(tx)

    paired_count = 0

    for user_id, items in transfers_by_user.items():
        items.sort(key=lambda item: item.transaction_id)

        for index in range(0, len(items) - 1, 2):
            first = items[index]
            second = items[index + 1]

            group_id = (
                f"TRF-{user_id}-{index // 2 + 1:04d}"
            )

            second.amount = first.amount
            first.transfer_group_id = group_id
            second.transfer_group_id = group_id

            first.category_id = "CAT-007"
            second.category_id = "CAT-007"

            paired_count += 2

        # An odd final transfer remains a single unmatched transfer.
        if len(items) % 2:
            items[-1].transfer_group_id = None

    print("Transfer legs paired:", paired_count)


def create_recurring_records(session, transactions):
    groups = defaultdict(list)

    recurring_merchants = {
        "MER-001", "MER-008", "MER-009", "MER-010", "MER-017"
    }

    for tx in transactions:
        if (
            tx.merchant_id in recurring_merchants
            and tx.transaction_type == "Expense"
            and tx.status == "Completed"
        ):
            groups[
                (tx.user_id, tx.account_id, tx.merchant_id)
            ].append(tx)

    created_series = 0
    created_occurrences = 0

    for (user_id, account_id, merchant_id), items in groups.items():
        items.sort(key=lambda item: item.transaction_date)

        # Require at least two payments before declaring a recurring series.
        if len(items) < 2:
            continue

        series_id = (
            f"DS-REC-{user_id}-{merchant_id}"
        )

        existing = session.get(RecurringSeries, series_id)
        if existing:
            continue

        merchant = session.get(Merchant, merchant_id)
        category_id = items[0].category_id or MERCHANT_CATEGORY[merchant_id]

        average_amount = (
            sum((tx.amount for tx in items), Decimal("0.00"))
            / Decimal(len(items))
        ).quantize(Decimal("0.01"))

        last_date = items[-1].transaction_date
        next_date = next_month(last_date)

        series = RecurringSeries(
            series_id=series_id,
            user_id=user_id,
            account_id=account_id,
            merchant_id=merchant_id,
            category_id=category_id,
            series_name=f"{merchant.merchant_name} Subscription",
            expected_amount=average_amount,
            frequency="Monthly",
            last_payment_date=last_date,
            next_payment_date=next_date,
            occurrence_count=len(items),
            status="Active",
        )

        session.add(series)
        session.flush()

        for tx in items:
            occurrence_id = (
                f"DS-OCC-{tx.transaction_id}"
            )

            existing_occurrence = session.get(
                RecurringOccurrence, occurrence_id
            )

            if existing_occurrence:
                continue

            session.add(RecurringOccurrence(
                occurrence_id=occurrence_id,
                series_id=series_id,
                transaction_id=tx.transaction_id,
                occurrence_date=tx.transaction_date,
                actual_amount=tx.amount,
                status="Matched",
            ))

            created_occurrences += 1

        created_series += 1

    session.commit()

    print("Recurring series created:", created_series)
    print("Recurring occurrences created:", created_occurrences)


def rebuild_ground_truth(transactions):
    path = DATA_DIR / "ground_truth.csv"

    fields = [
        "transaction_id",
        "expected_category_id",
        "is_intentionally_uncategorized",
        "merchant_id",
        "expected_transaction_type",
        "is_refund",
        "original_transaction_id",
        "is_transfer",
        "transfer_group_id",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for tx in transactions:
            if tx.transaction_type == "Income":
                expected_category = "CAT-006"
            elif tx.transaction_type == "Transfer":
                expected_category = "CAT-007"
            elif tx.transaction_type == "Refund":
                expected_category = tx.category_id or MERCHANT_CATEGORY.get(
                    tx.merchant_id
                )
            else:
                expected_category = MERCHANT_CATEGORY.get(
                    tx.merchant_id
                )

            writer.writerow({
                "transaction_id": tx.transaction_id,
                "expected_category_id": expected_category,
                "is_intentionally_uncategorized": (
                    tx.category_id is None
                    and tx.transaction_type == "Expense"
                ),
                "merchant_id": tx.merchant_id,
                "expected_transaction_type": tx.transaction_type,
                "is_refund": tx.transaction_type == "Refund",
                "original_transaction_id": tx.original_transaction_id,
                "is_transfer": tx.transaction_type == "Transfer",
                "transfer_group_id": tx.transfer_group_id,
            })

    print("Ground truth rebuilt for", len(transactions), "transactions")


def validate(session, transactions):
    transaction_ids = {tx.transaction_id for tx in transactions}

    invalid_refunds = 0
    linked_refunds = 0
    unmatched_refund_exceptions = 0
    refund_totals = defaultdict(float)
    invalid_transfers = 0

    for tx in transactions:
        if tx.transaction_type != "Refund":
            continue

        if not tx.original_transaction_id:
            unmatched_refund_exceptions += 1
            continue

        linked_refunds += 1
        original = session.get(Transaction, tx.original_transaction_id)

        if (
            original is None
            or original.transaction_type != "Expense"
            or original.user_id != tx.user_id
            or original.merchant_id != tx.merchant_id
            or original.transaction_date > tx.transaction_date
        ):
            invalid_refunds += 1
            continue

        refund_totals[original.transaction_id] += float(tx.amount)

    for original_id, total_refunded in refund_totals.items():
        original = session.get(Transaction, original_id)
        if total_refunded > float(original.amount) + 0.000001:
            invalid_refunds += 1

    transfer_groups = defaultdict(list)

    for tx in transactions:
        if tx.transaction_type == "Transfer" and tx.transfer_group_id:
            transfer_groups[tx.transfer_group_id].append(tx)

    for group_id, items in transfer_groups.items():
        if len(items) != 2:
            invalid_transfers += 1
        elif (
            items[0].user_id != items[1].user_id
            or items[0].amount != items[1].amount
        ):
            invalid_transfers += 1

    occurrence_count = session.query(RecurringOccurrence).filter(
        RecurringOccurrence.occurrence_id.like("DS-OCC-%")
    ).count()

    series_count = session.query(RecurringSeries).filter(
        RecurringSeries.series_id.like("DS-REC-%")
    ).count()

    ground_truth_path = DATA_DIR / "ground_truth.csv"

    with ground_truth_path.open(
        encoding="utf-8", newline=""
    ) as file:
        ground_truth_count = sum(1 for _ in csv.DictReader(file))

    report = {
        "seed": SEED,
        "transactions": len(transaction_ids),
        "ground_truth_rows": ground_truth_count,
        "total_refunds": linked_refunds + unmatched_refund_exceptions,
        "linked_refunds": linked_refunds,
        "unmatched_refund_exceptions": unmatched_refund_exceptions,
        "refunds_with_invalid_references": invalid_refunds,
        "invalid_transfer_groups": invalid_transfers,
        "recurring_series": series_count,
        "recurring_occurrences": occurrence_count,
        "passed": (
            len(transaction_ids) == 500000
            and ground_truth_count == 500000
            and linked_refunds == 13303
            and unmatched_refund_exceptions == 1068
            and invalid_refunds == 0
            and invalid_transfers == 0
        ),
    }

    with (DATA_DIR / "validation_report.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=4)

    print("\nENRICHMENT VALIDATION")
    print(json.dumps(report, indent=4))

    return report
def main():
    if not DB_PATH.exists():
        print("Dataset database not found:", DB_PATH)
        return

    session = Session()

    try:
        transactions = (
            session.query(Transaction)
            .filter(Transaction.transaction_id.like("DS-TXN-%"))
            .order_by(Transaction.transaction_id)
            .all()
        )

        print("Loaded transactions:", len(transactions))

        repair_refunds(session, transactions)
        pair_transfers(transactions)
        session.commit()

        create_recurring_records(session, transactions)
        rebuild_ground_truth(transactions)

        report = validate(session, transactions)

        if report["passed"]:
            print("\nDataset enrichment completed successfully!")
        else:
            print("\nSome validations failed. Review the report.")

    finally:
        session.close()


if __name__ == "__main__":
    main()

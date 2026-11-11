
def generate_transactions(session):
    transaction_batch = []
    ground_truth_batch = []

    transaction_number = 0
    start_time = datetime.now()

    for user_number in range(1, USER_COUNT + 1):
        user_id = f"DSU-{user_number:06d}"

        # Refund references are isolated per user.
        # Key = transaction_id, Value = original expense details.
        expense_records = {}

        # Track cumulative refund amount for every expense.
        refunded_amounts = {}

        for index in range(TRANSACTIONS_PER_USER):
            transaction_number += 1

            transaction_id = f"DS-TXN-{transaction_number:09d}"
            account_number = random.choice([1, 2])
            account_id = f"DSA-{user_number:06d}-{account_number:02d}"

            merchant_id, merchant_name = choose_merchant()

            if index % 30 == 0:
                merchant_id = "MER-015"
                merchant_name = "Salary"
                transaction_type = "Income"
            else:
                # Refund is selected only when a valid refundable
                # expense exists for this user.
                refundable_expenses = [
                    record
                    for record in expense_records.values()
                    if record["remaining"] > Decimal("0.00")
                ]

                choices = ["Expense", "Income", "Transfer"]
                weights = [82, 8, 7]

                if refundable_expenses:
                    choices.append("Refund")
                    weights.append(3)

                transaction_type = random.choices(
                    choices,
                    weights=weights,
                    k=1
                )[0]

            transfer_group_id = None
            if transaction_type == "Transfer":
                transfer_group_id = f"TRF-{transaction_number:09d}"

            original_transaction_id = None

            if transaction_type == "Refund":
                # Match refund to a previous expense from the same
                # user and same merchant, with sufficient balance.
                candidates = [
                    record
                    for record in refundable_expenses
                    if record["merchant_id"] == merchant_id
                ]

                if not candidates:
                    # If the randomly selected merchant has no
                    # matching expense, choose a valid expense.
                    candidates = refundable_expenses

                if candidates:
                    original = random.choice(candidates)
                    original_transaction_id = original["transaction_id"]

                    remaining = original["remaining"]
                    amount = min(
                        choose_amount(original["merchant_id"], "Expense"),
                        remaining
                    ).quantize(Decimal("0.01"))

                    original["remaining"] -= amount
                    refunded_amounts[original_transaction_id] += amount

                    merchant_id = original["merchant_id"]
                    merchant_name = original["merchant_name"]
                else:
                    # No valid original expense: generate a normal
                    # expense instead of an unlinked refund.
                    transaction_type = "Expense"
                    amount = choose_amount(merchant_id, "Expense")

            else:
                amount = choose_amount(merchant_id, transaction_type)

            transaction_date = random_transaction_date()

            if transaction_type == "Refund" and original_transaction_id:
                original_date = expense_records[
                    original_transaction_id
                ]["transaction_date"]

                # Refund must occur after its original expense.
                transaction_date = original_date + timedelta(
                    days=random.randint(1, 90)
                )

                if transaction_date > date(2026, 11, 9):
                    transaction_date = date(2026, 11, 9)

            elif merchant_id in (
                "MER-001", "MER-008", "MER-009", "MER-010"
            ):
                transaction_date = date(
                    random.randint(2025, 2026),
                    random.randint(1, 12),
                    1
                )

                transaction_date = max(
                    transaction_date, date(2025, 11, 10)
                )
                transaction_date = min(
                    transaction_date, date(2026, 11, 9)
                )

            aliases = ALIASES[merchant_name]
            description = random.choice(aliases)

            if (
                transaction_date.month in (10, 11, 12)
                and merchant_id in ("MER-002", "MER-013", "MER-012")
            ):
                amount = (amount * Decimal("1.30")).quantize(
                    Decimal("0.01")
                )

            expected_category_id = (
                "CAT-006" if transaction_type == "Income"
                else "CAT-007" if transaction_type == "Transfer"
                else MERCHANT_CATEGORY[merchant_id]
            )

            leave_uncategorized = (
                transaction_type == "Expense"
                and random.random() < 0.05
            )

            actual_category_id = (
                None if leave_uncategorized else expected_category_id
            )

            transaction_batch.append(Transaction(
                transaction_id=transaction_id,
                user_id=user_id,
                account_id=account_id,
                merchant_id=merchant_id,
                category_id=actual_category_id,
                transaction_date=transaction_date,
                description=description,
                amount=amount,
                transaction_type=transaction_type,
                status="Completed",
                original_transaction_id=original_transaction_id,
                transfer_group_id=transfer_group_id
            ))

            ground_truth_batch.append({
                "transaction_id": transaction_id,
                "expected_category_id": expected_category_id,
                "is_intentionally_uncategorized": leave_uncategorized,
                "merchant_id": merchant_id,
                "expected_transaction_type": transaction_type,
                "is_refund": transaction_type == "Refund",
                "original_transaction_id": original_transaction_id,
                "is_transfer": transaction_type == "Transfer",
                "transfer_group_id": transfer_group_id
            })

            if transaction_type == "Expense":
                expense_records[transaction_id] = {
                    "transaction_id": transaction_id,
                    "merchant_id": merchant_id,
                    "merchant_name": merchant_name,
                    "transaction_date": transaction_date,
                    "remaining": amount
                }
                refunded_amounts[transaction_id] = Decimal("0.00")

            if len(transaction_batch) >= BATCH_SIZE:
                session.add_all(transaction_batch)
                session.commit()
                transaction_batch.clear()

                append_ground_truth(ground_truth_batch)
                ground_truth_batch.clear()

                print(
                    f"Generated {transaction_number:,} "
                    f"/ {TOTAL_TRANSACTIONS:,} transactions"
                )

        if transaction_batch:
            session.add_all(transaction_batch)
            session.commit()
            transaction_batch.clear()

        if ground_truth_batch:
            append_ground_truth(ground_truth_batch)
            ground_truth_batch.clear()

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"Generated {transaction_number:,} transactions in {elapsed:.1f}s")

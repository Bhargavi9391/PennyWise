
from datetime import date

from database import (
    SessionLocal,
    UserProfile,
    Account,
    Merchant,
    Transaction
)


def seed_sample_data():
    session = SessionLocal()

    try:
        # 1. Create User
        user = session.get(UserProfile, "USR-000001")

        if user is None:
            user = UserProfile(
                user_id="USR-000001",
                full_name="Bhargavi",
                email="bhargavi@example.com"
            )
            session.add(user)

        # 2. Create Account
        account = session.get(
            Account,
            "ACC-USR-000001-01"
        )

        if account is None:
            account = Account(
                account_id="ACC-USR-000001-01",
                user_id="USR-000001",
                account_name="Primary Account",
                account_type="Savings"
            )
            session.add(account)

        # 3. Create Merchants
        merchants = [
            ("MER-001", "DMart"),
            ("MER-002", "Uber"),
            ("MER-003", "Amazon"),
            ("MER-004", "Company Salary")
        ]

        for merchant_id, merchant_name in merchants:
            existing = session.get(Merchant, merchant_id)

            if existing is None:
                session.add(
                    Merchant(
                        merchant_id=merchant_id,
                        merchant_name=merchant_name
                    )
                )

        # Save parent records first
        session.commit()

        # 4. Create Transactions
        transactions = [
            {
                "transaction_id": "TXN-2026-00000001",
                "merchant_id": "MER-001",
                "category_id": "CAT-001",
                "description": "Monthly groceries",
                "amount": 2450,
                "transaction_type": "Expense"
            },
            {
                "transaction_id": "TXN-2026-00000002",
                "merchant_id": "MER-002",
                "category_id": "CAT-002",
                "description": "Cab ride",
                "amount": 350,
                "transaction_type": "Expense"
            },
            {
                "transaction_id": "TXN-2026-00000003",
                "merchant_id": "MER-003",
                "category_id": "CAT-003",
                "description": "Online shopping",
                "amount": 1299,
                "transaction_type": "Expense"
            },
            {
                "transaction_id": "TXN-2026-00000004",
                "merchant_id": "MER-004",
                "category_id": "CAT-006",
                "description": "Monthly salary",
                "amount": 35000,
                "transaction_type": "Income"
            }
        ]

        for item in transactions:
            existing = session.get(
                Transaction,
                item["transaction_id"]
            )

            if existing is None:
                transaction = Transaction(
                    transaction_id=item["transaction_id"],
                    user_id="USR-000001",
                    account_id="ACC-USR-000001-01",
                    merchant_id=item["merchant_id"],
                    category_id=item["category_id"],
                    transaction_date=date(2026, 11, 10),
                    description=item["description"],
                    amount=item["amount"],
                    transaction_type=item["transaction_type"],
                    status="Completed"
                )

                session.add(transaction)

        session.commit()

        print("Sample data inserted successfully!")

    except Exception as error:
        session.rollback()
        print("Error inserting sample data:", error)

    finally:
        session.close()


if __name__ == "__main__":
    seed_sample_data()

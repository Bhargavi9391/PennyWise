
from database import SessionLocal, Category

def seed_categories():
    session = SessionLocal()

    categories = [
        Category(
            category_id="CAT-001",
            category_name="Food & Dining",
            category_type="Expense"
        ),
        Category(
            category_id="CAT-002",
            category_name="Transportation",
            category_type="Expense"
        ),
        Category(
            category_id="CAT-003",
            category_name="Shopping",
            category_type="Expense"
        ),
        Category(
            category_id="CAT-004",
            category_name="Housing",
            category_type="Expense"
        ),
        Category(
            category_id="CAT-005",
            category_name="Entertainment",
            category_type="Expense"
        ),
        Category(
            category_id="CAT-006",
            category_name="Income",
            category_type="Income"
        ),
        Category(
            category_id="CAT-007",
            category_name="Transfer",
            category_type="Transfer"
        )
    ]

    try:
        for category in categories:
            existing = session.get(
                Category,
                category.category_id
            )

            if existing is None:
                session.add(category)

        session.commit()
        print("Default categories inserted successfully!")

    except Exception as error:
        session.rollback()
        print("Error:", error)

    finally:
        session.close()


if __name__ == "__main__":
    seed_categories()

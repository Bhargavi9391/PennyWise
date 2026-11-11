

import sqlite3
import calendar
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

DB_PATH = Path("pennywise_dataset.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

try:
    # Avoid duplicate generation
    existing = cursor.execute(
        "SELECT COUNT(*) FROM budgets"
    ).fetchone()[0]

    if existing > 0:
        raise Exception(
            f"Budgets table already has {existing} records. "
            "Stopping to avoid duplicates."
        )

    # Get expense categories
    categories = cursor.execute("""
        SELECT category_id
        FROM categories
        WHERE category_type = 'Expense'
        ORDER BY category_id
    """).fetchall()

    # Get all users
    users = cursor.execute("""
        SELECT user_id
        FROM user_profiles
        ORDER BY user_id
    """).fetchall()

    # Find transaction date range
    date_range = cursor.execute("""
        SELECT MIN(date(transaction_date)),
               MAX(date(transaction_date))
        FROM transactions
    """).fetchone()

    start_date = date.fromisoformat(date_range[0])
    end_date = date.fromisoformat(date_range[1])

    # Get actual completed expenses by user/category/month
    spending_rows = cursor.execute("""
        SELECT
            user_id,
            category_id,
            strftime('%Y-%m', transaction_date) AS month,
            SUM(ABS(amount)) AS total_spending
        FROM transactions
        WHERE transaction_type = 'Expense'
          AND status = 'Completed'
          AND category_id IS NOT NULL
        GROUP BY user_id, category_id, month
    """).fetchall()

    spending = {
        (user_id, category_id, month): Decimal(str(total))
        for user_id, category_id, month, total in spending_rows
    }

    # Generate calendar months overlapping transaction period
    months = []
    current = date(start_date.year, start_date.month, 1)

    while current <= end_date:
        last_day = calendar.monthrange(
            current.year, current.month
        )[1]

        period_start = max(current, start_date)
        period_end = min(
            date(current.year, current.month, last_day),
            end_date
        )

        months.append((
            current.strftime("%Y-%m"),
            period_start.isoformat(),
            period_end.isoformat()
        ))

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    total_created = 0

    for user_row in users:
        user_id = user_row[0]

        for month, period_start, period_end in months:
            for category_row in categories:
                category_id = category_row[0]

                actual = spending.get(
                    (user_id, category_id, month),
                    Decimal("0")
                )

                # Budget = actual spending + 10%
                # Minimum budget = Rs. 500
                budget_amount = max(
                    actual * Decimal("1.10"),
                    Decimal("500")
                )

                budget_amount = budget_amount.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP
                )

                budget_id = (
                    f"BUD-{user_id}-{month}-{category_id}"
                )

                # Latest month remains Active
                status = (
                    "Active"
                    if month == months[-1][0]
                    else "Inactive"
                )

                cursor.execute("""
                    INSERT INTO budgets (
                        budget_id,
                        user_id,
                        category_id,
                        budget_amount,
                        period_start,
                        period_end,
                        status,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    budget_id,
                    user_id,
                    category_id,
                    str(budget_amount),
                    period_start,
                    period_end,
                    status,
                    datetime.now().isoformat()
                ))

                total_created += 1

    conn.commit()

    print("\nBUDGET GENERATION SUCCESSFUL!")
    print("Users:", len(users))
    print("Expense categories:", len(categories))
    print("Calendar months:", len(months))
    print("Budgets created:", total_created)

    print("\nMONTHLY PERIODS:")
    for month, period_start, period_end in months:
        print(month, period_start, "to", period_end)

    print("\nBUDGET SUMMARY:")
    print(*cursor.execute("""
        SELECT status, COUNT(*), ROUND(SUM(budget_amount), 2)
        FROM budgets
        GROUP BY status
    """).fetchall(), sep="\n")

except Exception:
    conn.rollback()
    raise

finally:
    conn.close()


import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("pennywise_dataset.db")

# Explicit, documented business rules.
# Higher priority rules are evaluated first.
RULES = [
    # Income
    ("Salary credit", "CAT-006", "SALARY", 100),
    ("Monthly salary", "CAT-006", "PAYROLL", 100),

    # Food and dining
    ("Food delivery Swiggy", "CAT-001", "SWIGGY", 90),
    ("Food delivery Zomato", "CAT-001", "ZOMATO", 90),
    ("BigBasket groceries", "CAT-001", "BIGBASKET", 90),
    ("Grocery store", "CAT-001", "KIRANA", 80),
    ("Local grocery", "CAT-001", "LOCAL MART", 80),
    ("General store", "CAT-001", "GENERAL STORE", 80),
    ("Supermarket", "CAT-001", "SUPERMARTS", 80),
    ("Instamart groceries", "CAT-001", "INSTAMART", 80),

    # Transportation
    ("Uber rides", "CAT-002", "UBER", 90),
    ("Ola rides", "CAT-002", "OLA", 90),
    ("Railway tickets", "CAT-002", "IRCTC", 90),
    ("Indian Railways", "CAT-002", "RAILWAYS", 90),
    ("Fuel payment", "CAT-002", "FUEL", 90),
    ("Petrol pump", "CAT-002", "PETROL", 90),

    # Shopping
    ("Amazon shopping", "CAT-003", "AMAZON", 90),
    ("Amazon abbreviation", "CAT-003", "AMZN", 90),
    ("Flipkart shopping", "CAT-003", "FLIPKART", 90),
    ("FK online shopping", "CAT-003", "FK ONLINE", 90),

    # Housing and utilities
    ("Airtel bill", "CAT-004", "AIRTEL", 90),
    ("Jio bill", "CAT-004", "JIO", 90),
    ("Electricity bill", "CAT-004", "ELECTRICITY", 90),
    ("Electricity board", "CAT-004", "EB BILL", 90),
    ("Water bill", "CAT-004", "WATER", 90),

    # Entertainment
    ("Netflix subscription", "CAT-005", "NETFLIX", 90),
    ("Movie theatre INOX", "CAT-005", "INOX", 90),
    ("Movie ticket", "CAT-005", "MOVIE TICKET", 90),
]

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

try:
    rule_count = cursor.execute(
        "SELECT COUNT(*) FROM category_rules"
    ).fetchone()[0]

    history_count = cursor.execute(
        "SELECT COUNT(*) FROM transaction_categorizations"
    ).fetchone()[0]

    if rule_count or history_count:
        raise Exception(
            "Rules/history already exist. "
            "Stopping to avoid duplicate records."
        )

    # Determine effective date range from source transactions.
    date_range = cursor.execute("""
        SELECT MIN(date(transaction_date)),
               MAX(date(transaction_date))
        FROM transactions
    """).fetchone()

    effective_from = date_range[0]
    effective_to = date_range[1]

    now = datetime.now().isoformat()

    # Insert category rules.
    rule_records = []

    for index, (name, category_id, keyword, priority) in enumerate(
        RULES, start=1
    ):
        rule_records.append((
            f"DS-RULE-{index:03d}",
            category_id,
            name,
            "description",
            "contains",
            keyword,
            priority,
            1,
            effective_from,
            effective_to,
            now
        ))

    cursor.executemany("""
        INSERT INTO category_rules (
            rule_id,
            category_id,
            rule_name,
            match_field,
            match_type,
            match_value,
            priority,
            is_active,
            effective_from,
            effective_to,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rule_records)

    # Load rules in priority order.
    rules = cursor.execute("""
        SELECT rule_id, category_id, match_value
        FROM category_rules
        WHERE is_active = 1
        ORDER BY priority DESC, rule_id
    """).fetchall()

    # Read transactions in batches.
    transaction_cursor = conn.cursor()
    transaction_cursor.execute("""
        SELECT transaction_id, description, transaction_date
        FROM transactions
        WHERE transaction_type IN ('Expense', 'Income')
          AND status = 'Completed'
        ORDER BY transaction_id
    """)

    matched = 0
    unmatched = 0
    batch = []

    while True:
        transactions = transaction_cursor.fetchmany(5000)

        if not transactions:
            break

        for transaction_id, description, transaction_date in transactions:
            description_upper = (description or "").upper()

            selected_rule = None

            for rule_id, category_id, keyword in rules:
                if keyword.upper() in description_upper:
                    selected_rule = (
                        rule_id,
                        category_id,
                        keyword
                    )
                    break

            if selected_rule:
                rule_id, category_id, keyword = selected_rule

                batch.append((
                    f"DS-DEC-{transaction_id}",
                    transaction_id,
                    rule_id,
                    category_id,
                    "description",
                    keyword,
                    "RULE",
                    now
                ))

                matched += 1
            else:
                unmatched += 1

        if len(batch) >= 5000:
            cursor.executemany("""
                INSERT INTO transaction_categorizations (
                    decision_id,
                    transaction_id,
                    rule_id,
                    category_id,
                    matched_field,
                    matched_value,
                    decision_method,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)

            batch.clear()

    if batch:
        cursor.executemany("""
            INSERT INTO transaction_categorizations (
                decision_id,
                transaction_id,
                rule_id,
                category_id,
                matched_field,
                matched_value,
                decision_method,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)

    conn.commit()

    print("\nCATEGORY RULE GENERATION SUCCESSFUL!")
    print("Rules created:", len(rule_records))
    print("Transactions matched:", matched)
    print("Transactions unmatched:", unmatched)

    print("\nRULE SUMMARY:")
    print(*cursor.execute("""
        SELECT category_id, COUNT(*)
        FROM category_rules
        GROUP BY category_id
        ORDER BY category_id
    """).fetchall(), sep="\n")

    print("\nHISTORY RECORDS:")
    print(cursor.execute(
        "SELECT COUNT(*) FROM transaction_categorizations"
    ).fetchone()[0])

except Exception:
    conn.rollback()
    raise

finally:
    conn.close()

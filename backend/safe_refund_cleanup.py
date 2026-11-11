import sqlite3
import shutil
import os

DB = "pennywise_dataset.db"
BACKUP = "pennywise_dataset_pre_safe_refund_cleanup.db"

if not os.path.exists(DB):
    raise FileNotFoundError(DB)

if os.path.exists(BACKUP):
    raise FileExistsError(
        f"Backup already exists: {BACKUP}. Stopping safely."
    )

# Create a fresh backup before modifying anything
shutil.copy2(DB, BACKUP)
print("Backup created:", BACKUP)

conn = sqlite3.connect(DB)

try:
    before = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE transaction_type = 'Refund'
          AND original_transaction_id IS NOT NULL
    """).fetchone()[0]

    conn.execute("""
        UPDATE transactions
        SET original_transaction_id = NULL
        WHERE transaction_type = 'Refund'
    """)

    conn.commit()

    after = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE transaction_type = 'Refund'
          AND original_transaction_id IS NOT NULL
    """).fetchone()[0]

    total = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE transaction_type = 'Refund'
    """).fetchone()[0]

    print("Refunds processed:", total)
    print("Links cleared:", before)
    print("Remaining original links:", after)

finally:
    conn.close()
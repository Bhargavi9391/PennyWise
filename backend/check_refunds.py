
import sqlite3

conn = sqlite3.connect("pennywise_dataset.db")
cur = conn.cursor()

# Check if total refunds exceed original expense
query = """
SELECT
    o.transaction_id,
    o.amount,
    COUNT(r.transaction_id),
    ROUND(SUM(r.amount), 2),
    ROUND(o.amount - SUM(r.amount), 2)
FROM transactions o
JOIN transactions r
    ON r.original_transaction_id = o.transaction_id
WHERE o.transaction_type = 'Expense'
  AND r.transaction_type = 'Refund'
GROUP BY o.transaction_id, o.amount
HAVING SUM(r.amount) > o.amount
LIMIT 10
"""

rows = cur.execute(query).fetchall()

print("OVER-REFUNDED TRANSACTIONS:")
print("Count shown (maximum 10):", len(rows))
for row in rows:
    print(row)

# Check refund links to another user's transaction
mismatch_query = """
SELECT COUNT(*)
FROM transactions r
JOIN transactions o
    ON r.original_transaction_id = o.transaction_id
WHERE r.transaction_type = 'Refund'
  AND r.user_id <> o.user_id
"""

mismatch = cur.execute(mismatch_query).fetchone()[0]

print("\nREFUND USER MISMATCHES:", mismatch)

conn.close()

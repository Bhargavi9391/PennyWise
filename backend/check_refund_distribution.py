
import sqlite3

conn = sqlite3.connect("pennywise_dataset.db")
cur = conn.cursor()

queries = {
    "TOTAL REFUNDS": """
        SELECT COUNT(*) FROM transactions
        WHERE transaction_type = 'Refund'
    """,
    "UNIQUE ORIGINAL TRANSACTIONS": """
        SELECT COUNT(DISTINCT original_transaction_id)
        FROM transactions
        WHERE transaction_type = 'Refund'
    """,
    "REFUNDS PER ORIGINAL": """
        SELECT COUNT(*) AS refund_count, COUNT(DISTINCT original_transaction_id)
        FROM transactions
        WHERE transaction_type = 'Refund'
        GROUP BY original_transaction_id
        ORDER BY refund_count DESC
        LIMIT 10
    """,
    "REFUND AMOUNT SAMPLE": """
        SELECT
            o.transaction_id,
            o.amount AS original_amount,
            r.transaction_id,
            r.amount AS refund_amount,
            r.transaction_date
        FROM transactions o
        JOIN transactions r
          ON r.original_transaction_id = o.transaction_id
        WHERE r.transaction_type = 'Refund'
        LIMIT 10
    """
}

for title, query in queries.items():
    print("\n" + title)
    print("-" * 40)
    for row in cur.execute(query):
        print(row)

conn.close()


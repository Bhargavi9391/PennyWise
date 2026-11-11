import sqlite3
import csv
import shutil
from pathlib import Path

folder = Path("dataset_exports")
csv_path = folder / "ground_truth.csv"
backup_path = folder / "ground_truth_pre_repair.csv"
temp_path = folder / "ground_truth_temp.csv"

if not csv_path.exists():
    raise FileNotFoundError(csv_path)

if backup_path.exists():
    raise FileExistsError("Ground truth backup already exists. Stop and check.")

shutil.copy2(csv_path, backup_path)

conn = sqlite3.connect("pennywise_dataset.db")

refund_links = dict(conn.execute("""
    SELECT transaction_id, original_transaction_id
    FROM transactions
    WHERE transaction_type='Refund'
""").fetchall())

linked = sum(v is not None for v in refund_links.values())
unlinked = len(refund_links) - linked

updated_rows = 0

try:
    with open(csv_path, "r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)

        with open(temp_path, "w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                if row["transaction_id"] in refund_links:
                    value = refund_links[row["transaction_id"]]
                    row["original_transaction_id"] = value or ""
                    updated_rows += 1

                writer.writerow(row)

    if updated_rows != 14371:
        raise ValueError(f"Expected 14371 refunds, found {updated_rows}")

    if linked != 13303 or unlinked != 1068:
        raise ValueError("Database refund counts do not match repair report")

    temp_path.replace(csv_path)

    print("GROUND TRUTH SYNCHRONIZED")
    print("Rows updated:", updated_rows)
    print("Linked refunds:", linked)
    print("Unlinked exceptions:", unlinked)
    print("Other columns preserved: YES")
    print("Original CSV backup:", backup_path)

except Exception:
    if temp_path.exists():
        temp_path.unlink()
    raise

finally:
    conn.close()
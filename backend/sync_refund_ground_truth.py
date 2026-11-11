
import csv
import os
import shutil

FILE = "dataset_exports/ground_truth.csv"
BACKUP = "dataset_exports/ground_truth_before_refund_sync.csv"
TEMP = "dataset_exports/ground_truth_temp.csv"

if not os.path.exists(FILE):
    raise FileNotFoundError(FILE)

if os.path.exists(BACKUP):
    raise FileExistsError("Backup already exists. Stopping safely.")

shutil.copy2(FILE, BACKUP)

with open(FILE, "r", newline="", encoding="utf-8-sig") as source:
    reader = csv.DictReader(source)
    fieldnames = reader.fieldnames
    rows = list(reader)

refund_count = 0

for row in rows:
    if row["expected_transaction_type"] == "Refund":
        row["original_transaction_id"] = ""
        refund_count += 1

with open(TEMP, "w", newline="", encoding="utf-8-sig") as output:
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

os.replace(TEMP, FILE)

print("Ground truth backup created:", BACKUP)
print("Total rows preserved:", len(rows))
print("Refund rows synchronized:", refund_count)
print("Refund original references cleared.")

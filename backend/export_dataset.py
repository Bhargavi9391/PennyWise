
import sqlite3
import csv
import json
from pathlib import Path

DB_PATH = Path("pennywise_dataset.db")
EXPORT_DIR = Path("exports")

EXPORT_DIR.mkdir(exist_ok=True)

if not DB_PATH.exists():
    raise FileNotFoundError("pennywise_dataset.db not found!")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

cursor = conn.cursor()

tables = cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""").fetchall()

summary = {}

for table_row in tables:
    table_name = table_row["name"]

    rows = cursor.execute(
        f'SELECT * FROM "{table_name}"'
    ).fetchall()

    columns = [item["name"] for item in cursor.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()]

    # Export CSV
    csv_path = EXPORT_DIR / f"{table_name}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(columns)

        for row in rows:
            writer.writerow([row[column] for column in columns])

    # Export JSON
    json_path = EXPORT_DIR / f"{table_name}.json"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(
            [dict(row) for row in rows],
            file,
            indent=2,
            default=str
        )

    summary[table_name] = len(rows)

    print(f"{table_name}: {len(rows)} rows exported")

# Export complete SQL database
sql_path = EXPORT_DIR / "pennywise_dataset.sql"

with open(sql_path, "w", encoding="utf-8") as file:
    for line in conn.iterdump():
        file.write(line + "\n")

conn.close()

# Export summary
with open(
    EXPORT_DIR / "export_summary.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(summary, file, indent=2)

print("\nEXPORT COMPLETED SUCCESSFULLY!")
print(f"Export folder: {EXPORT_DIR.resolve()}")
print(f"Tables exported: {len(summary)}")

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "v2_full_run2"
RULES = ROOT / "reproducibility_tests" / "category_rules.csv"
OUT = ROOT / "dataset_exports"
OUT.mkdir(exist_ok=True)

TABLES = [
    ("user_profiles", "user_id"),
    ("merchants", "merchant_id"),
    ("categories", "category_id"),
    ("accounts", "account_id"),
    ("category_rules", "rule_id"),
    ("transactions", "transaction_id"),
    ("budgets", "budget_id"),
    ("recurring_series", "series_id"),
    ("recurring_occurrences", "occurrence_id"),
    ("insights", "insight_id"),
    ("ground_truth", "transaction_id"),
]

FK = {
    "accounts": ["FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)"],
    "budgets": [
        "FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)",
        "FOREIGN KEY(category_id) REFERENCES categories(category_id)"
    ],
    "category_rules": [
        "FOREIGN KEY(category_id) REFERENCES categories(category_id)"
    ],
    "transactions": [
        "FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)",
        "FOREIGN KEY(account_id) REFERENCES accounts(account_id)",
        "FOREIGN KEY(merchant_id) REFERENCES merchants(merchant_id)",
        "FOREIGN KEY(category_id) REFERENCES categories(category_id)",
        "FOREIGN KEY(original_transaction_id) REFERENCES transactions(transaction_id)"
    ],
    "recurring_series": [
        "FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)",
        "FOREIGN KEY(account_id) REFERENCES accounts(account_id)",
        "FOREIGN KEY(merchant_id) REFERENCES merchants(merchant_id)",
        "FOREIGN KEY(category_id) REFERENCES categories(category_id)"
    ],
    "recurring_occurrences": [
        "FOREIGN KEY(series_id) REFERENCES recurring_series(series_id)",
        "FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id)"
    ],
    "insights": ["FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)"],
    "ground_truth": [
        "FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id)"
    ]
}

def quote(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"

sources = {}
for table, pk in TABLES:
    path = RULES if table == "category_rules" else BASE / f"{table}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        sources[table] = (path, reader.fieldnames)

sql_path = OUT / "v2_seed.sql"
summary = {}

with sql_path.open("w", encoding="utf-8", newline="\n") as sql:
    sql.write("-- PennyWise V2 deterministic dataset SQL seed\n")
    sql.write("-- Source: v2_full_run2 CSVs and reproducibility_tests/category_rules.csv\n")
    sql.write("-- Ground truth is stored separately from transaction input.\n\n")
    sql.write("PRAGMA foreign_keys = ON;\nBEGIN TRANSACTION;\n\n")

    # Create every table before inserting records.
    for table, pk in TABLES:
        _, columns = sources[table]
        definitions = [f'"{c}" TEXT' for c in columns]
        definitions.append(f'PRIMARY KEY ("{pk}")')
        definitions.extend(FK.get(table, []))
        sql.write(
            f'CREATE TABLE "{table}" (\n    '
            + ",\n    ".join(definitions)
            + "\n);\n\n"
        )

    # Stream CSV rows to avoid loading the 500K dataset into memory.
    for table, pk in TABLES:
        path, columns = sources[table]
        count = 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                values = []
                for col in columns:
                    value = row[col]
                    if value == "" and col in (
                        "category_id", "original_transaction_id"
                    ):
                        value = None
                    values.append(quote(value))

                sql.write(
                    f'INSERT INTO "{table}" ('
                    + ", ".join(f'"{c}"' for c in columns)
                    + ") VALUES ("
                    + ", ".join(values)
                    + ");\n"
                )
                count += 1
        summary[table] = count
        print(f"{table}: {count} rows")

    sql.write("\nCOMMIT;\n")

summary["total_rows"] = sum(summary.values())
summary["sql_file"] = str(sql_path)
summary["ground_truth_separate"] = True

(OUT / "v2_sql_export_summary.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)

print("\nV2 SQL EXPORT COMPLETED")
print("SQL:", sql_path)
print("Total rows:", summary["total_rows"])

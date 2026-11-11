
from pathlib import Path
import sqlite3
import hashlib
import json
from datetime import datetime

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
DB = BACKEND / "pennywise_dataset.db"
EXPORTS = BACKEND / "exports"
DATA_EXPORTS = BACKEND / "dataset_exports"

if not DB.exists():
    raise FileNotFoundError(f"Dataset database not found: {DB}")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

tables = [
    row["name"] for row in conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
]

counts = {
    table: conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    for table in tables
}

# Exact schema DDL from SQLite; no table data is included.
schema_rows = conn.execute("""
    SELECT type, name, sql
    FROM sqlite_master
    WHERE sql IS NOT NULL
      AND type IN ('table', 'index')
      AND name NOT LIKE 'sqlite_%'
    ORDER BY type, name
""").fetchall()

schema_sql = "\n\n".join(row["sql"] + ";" for row in schema_rows)
(ROOT / "schema.sql").write_text(schema_sql + "\n", encoding="utf-8")

# Data dictionary generated from actual database metadata.
dictionary = [
    "# PennyWise Data Dictionary",
    "",
    "Generated from the actual SQLite database using PRAGMA metadata.",
    ""
]

for table in tables:
    dictionary += [f"## {table}", "", "| Column | Data type | Primary key | Nullable | Foreign key |",
                   "|---|---|---|---|---|"]
    columns = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    foreign_keys = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
    fk_map = {fk["from"]: f'{fk["table"]}.{fk["to"]}' for fk in foreign_keys}

    for col in columns:
        dictionary.append(
            f'| {col["name"]} | {col["type"] or " unspecified "} | '
            f'{"Yes" if col["pk"] else "No"} | '
            f'{"No" if col["notnull"] or col["pk"] else "Yes"} | '
            f'{fk_map.get(col["name"], "-")} |'
        )
    dictionary.append("")

(ROOT / "DATA_DICTIONARY.md").write_text(
    "\n".join(dictionary), encoding="utf-8"
)

# ER diagram based on actual foreign-key relationships.
er = [
    "# PennyWise Entity Relationship Diagram",
    "",
    "Relationships below are derived from the SQLite foreign-key definitions.",
    "",
    "```mermaid",
    "erDiagram"
]

for table in tables:
    er.append(f"    {table} {{")
    for col in conn.execute(f'PRAGMA table_info("{table}")'):
        marker = " PK" if col["pk"] else ""
        er.append(f'        {col["type"] or "TEXT"} {col["name"]}{marker}')
    er.append("}")

for table in tables:
    for fk in conn.execute(f'PRAGMA foreign_key_list("{table}")'):
        er.append(
            f'    {fk["table"]} ||--o{{ {table} : "{fk["from"]}"'
        )

er += ["```", ""]
(ROOT / "ER_DIAGRAM.md").write_text("\n".join(er), encoding="utf-8")

# Dataset README.
manifest_path = DATA_EXPORTS / "source_manifest.json"
manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

seed = manifest.get("seed", 20261022)

readme = f"""# PennyWise

## Business problem

Categorize financial transactions, identify recurring payments, and compare
household spending against budgets.

## Solution

PennyWise provides a transaction-processing workflow with category rules,
categorization history, recurring payment records, budgets, and insights.
It also includes a synthetic dataset for validation and analysis.

## Technology

- Frontend: React
- Backend: Python Flask
- Database: SQLite
- Data processing: Python, SQLAlchemy, SQLite
- Dataset exports: CSV and JSON

## Project structure

- `frontend/` - application frontend
- `backend/` - API, operational database, dataset database, and scripts
- `backend/pennywise.db` - operational application database
- `backend/pennywise_dataset.db` - synthetic dataset database
- `backend/exports/` - entity-level CSV, JSON and SQL exports
- `backend/dataset_exports/` - ground truth, validation report and manifest
- `schema.sql` - exact dataset database schema
- `DATA_DICTIONARY.md` - columns, types and foreign-key references
- `ER_DIAGRAM.md` - entity relationship diagram

## Dataset snapshot

- Users: {counts.get("user_profiles", 0):,}
- Accounts: {counts.get("accounts", 0):,}
- Transactions: {counts.get("transactions", 0):,}
- Merchants: {counts.get("merchants", 0):,}
- Categories: {counts.get("categories", 0):,}
- Category rules: {counts.get("category_rules", 0):,}
- Budgets: {counts.get("budgets", 0):,}
- Recurring series: {counts.get("recurring_series", 0):,}
- Recurring occurrences: {counts.get("recurring_occurrences", 0):,}
- Categorization decisions: {counts.get("transaction_categorizations", 0):,}
- Edge-case scenarios: {counts.get("edge_case_scenarios", 0):,}
- Insights in synthetic dataset: {counts.get("insights", 0):,}

The dataset uses seed `{seed}`. The operational application database is
separate from the synthetic dataset database; their identifiers and records
must not be mixed.

## Main workflow

1. Load user, account, merchant and category master data.
2. Apply category rules to transaction descriptions.
3. Store categorization decisions for traceability.
4. Detect recurring payment series and occurrences.
5. Compare completed expenses against category budgets.
6. Generate insights for relevant spending and recurring-payment conditions.
7. Export data and validate database relationships.

## Data quality and traceability

- Primary keys identify records.
- Foreign keys represent parent-child relationships.
- Transaction categorization decisions are stored separately.
- Refunds can reference their original transactions.
- Transfer transactions can be associated through a transfer group.
- Recurring payments use series and occurrence records.
- Edge-case scenarios document expected exception behavior.
- Ground-truth labels are maintained separately from transaction input data.

## Commands

Run commands from the `backend` directory with the project virtual environment activated.

Validate the current dataset:

```cmd
python -c "import enrich_dataset as e; s=e.Session(); tx=s.query(e.Transaction).filter(e.Transaction.transaction_id.like('DS-TXN-%')).order_by(e.Transaction.transaction_id).all(); print('Loaded transactions:',len(tx)); report=e.validate(s,tx); s.close(); print('FINAL VALIDATION:', 'PASSED' if report['passed'] else 'FAILED')"
```

Export all dataset tables:

```cmd
python export_dataset.py
```

The export script writes CSV and JSON files to `backend/exports/`.
Do not run `enrich_dataset.py` as a harmless validation command: its main
routine performs data enrichment and can modify existing records.

## Validation snapshot

See `backend/dataset_exports/validation_report.json` for the recorded
validation result. Re-run the validation command above to check the current
database state.

## Reproducibility note

The recorded seed is `{seed}`. The existing dataset snapshot and its
validation artifacts are provided. The transaction-generation function
currently depends on configuration supplied externally; do not assume
`generate_dataset.py` is a standalone command. Review and configure the
generation pipeline before attempting a fresh full regeneration.

## Edge-case scenarios

The dataset documents five scenarios:
- Transfer double counting
- Refund treated as a new expense
- Missing recurring payment
- Timezone boundary
- Invalid budget category

Scenario definitions are not, by themselves, proof that each scenario has
passed an executable test. Refer to the test evidence before marking them
passed.
"""

(ROOT / "README.md").write_text(readme, encoding="utf-8")

# Refresh checksum only when the exported transaction CSV exists.
transaction_csv = DATA_EXPORTS / "transactions.csv"
if transaction_csv.exists() and manifest_path.exists():
    manifest["transaction_csv_sha256"] = hashlib.sha256(
        transaction_csv.read_bytes()
    ).hexdigest()
    manifest["checksum_updated_at"] = datetime.now().isoformat(timespec="seconds")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

conn.close()

print("DOCUMENTATION CREATED")
for name in ["README.md", "schema.sql", "DATA_DICTIONARY.md", "ER_DIAGRAM.md"]:
    path = ROOT / name
    print(name, "-", path.stat().st_size, "bytes")

print("Dataset tables:", len(tables))
print("Dataset transactions:", counts.get("transactions", 0))
print("Dataset records were not modified.")

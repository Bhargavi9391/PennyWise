# PennyWise

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

- Users: 1,000
- Accounts: 2,000
- Transactions: 500,000
- Merchants: 20
- Categories: 7
- Category rules: 28
- Budgets: 65,000
- Recurring series: 5,000
- Recurring occurrences: 51,750
- Categorization decisions: 365,177
- Edge-case scenarios: 5
- Insights in synthetic dataset: 0

The dataset uses seed `20261022`. The operational application database is
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

The recorded seed is `20261022`. The existing dataset snapshot and its
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

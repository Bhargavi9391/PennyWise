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

## Legacy SQLite Dataset Snapshot (Historical)

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
- Insights in original synthetic dataset: 0 (legacy snapshot; final V2 has 1,000)

The counts above describe the historical SQLite snapshot, not the final V2 dataset. The original SQLite snapshot was not independently regenerated. Final V2 generation and reproducibility results are documented separately below. The operational application database is separate from the synthetic dataset database; their identifiers and records must not be mixed.

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


## Verified testing results (2026-11-12)

- Dataset integrity: PASS (500,000 transactions).
- SQLite foreign-key violations: 0.
- Edge-case executable tests: 5/5 PASS, using an isolated database copy.
- Backend GET API smoke tests: 8/8 PASS.
- Frontend production build: PASS.
- Small deterministic generator: PASS (2 runs, 100 transactions, seed 20261022).
- Original SQLite snapshot reproducibility: not verified. Final V2 CSV reproducibility: PASS (11/11 files, seed 20261022).

The small reproducibility test uses
`backend/reproducibility_tests/generate_small.py`.

Its recorded results are in
`backend/reproducibility_tests/reproducibility_report.json`.

The edge-case test results are in
`backend/dataset_exports/edge_case_test_report.json`.

These tests do not establish that the original 500,000-row dataset can be
regenerated byte-for-byte from the current generation scripts.

## Local Setup
Backend: cd backend; venv\Scripts\activate; pip install -r requirements.txt; python app.py
Frontend: cd frontend; npm install; npm run dev
Backend URL: http://127.0.0.1:5000
Note: pennywise.db is operational; pennywise_dataset.db is synthetic. Keep them separate.

## V2 Final Dataset (Validated)

Users: 1,000 | Accounts: 2,000 | Merchants: 21 | Categories: 7

Transactions: 500,000 | Ground truth: 500,000 | Budgets: 60,000

Recurring series: 3,000 | Occurrences: 36,000 | Insights: 1,000

Refunds: 12,990 | Labelled edge-case scenarios: 5

Signed amounts, paired transfers, linked refunds, and monthly recurring payments are supported.

Full V2 validation: PASS. Two independent full runs using seed `20261022` produced matching counts and SHA-256 checksums for all 11 CSV files.

Generate: python backend/generate_configurable_v2.py --users 1000 --transactions-per-user 500 --output-dir backend/v2_full_run1

Validate: python backend/validate_full_dataset_v2.py --dataset-dir backend/v2_full_run1 --transactions-per-user 500

Generated CSV folders are excluded from Git.

## V2 Evaluation and Export Evidence (2026-11-12)

### Reproducibility
- Generator: `generate_configurable_v2.py`
- Fixed seed: `20261022`
- Users: 1,000
- Transactions: 500,000
- Two independent full runs completed.
- Final V2 CSV SHA-256 comparison: 11/11 files matched across two full runs.
- Dataset counts matched across both runs.
- V2 reproducibility report: `backend/dataset_exports/v2_reproducibility_report.json`
- V2 manifest: `backend/dataset_exports/v2_manifest.json`

This proves reproducibility of the standalone V2 CSV generator,
not byte-for-byte reproduction of the original SQLite database.

### Categorization Evaluation
Dataset: `v2_full_run2`

- Transactions: 500,000
- Evaluated transactions: 483,189
- Intentionally uncategorized exclusions: 16,811
- Accuracy: 57.05%
- Rule coverage: 67.50%
- Macro precision: 73.27%
- Macro recall: 59.55%
- Macro F1: 63.69%

Evaluation uses 28 description-based category rules.
Transfer categorization requires separate business logic.
See `backend/dataset_exports/v2_categorization_evaluation_report.json`
and `v2_categorization_predictions.csv`.

### Recurring Integrity Evaluation
- Recurring series: 3,000
- Recurring occurrences: 36,000
- Regular intervals: 3,000
- Occurrence count mismatches: 0
- Missing occurrence series: 0
- Date-order errors: 0
- Account, merchant and category mismatches: 0
- Amount mismatches over 10%: 0
- Integrity-only evaluation does not calculate precision/recall. A separate generator-labelled, group-level detector evaluation reports precision 100%, recall 99.97%, and F1 99.98% (2,999 TP, 0 FP, 1 FN). This is an offline detector evaluation, not a direct Flask endpoint test.

Report: `backend/dataset_exports/v2_recurring_evaluation_report.json`

### V2 Export Deliverables

CSV:
`backend/v2_final_run2/`

JSON:
`backend/v2_final_run2/json/`

Category rules:
- `backend/dataset_exports/v2_category_rules.csv`
- `backend/dataset_exports/v2_category_rules.json`

SQL:
- `backend/dataset_exports/v2_seed.sql`
- `backend/dataset_exports/v2_sql_export_summary.json`

SQL verification:
- SQL execution: PASS
- Foreign-key violations: 0
- Transactions: 500,000
- Ground-truth records: 500,000
- SQLite integrity check: OK

The SQL seed contains 1,103,056 records across 11 tables.
Ground-truth labels are maintained in a separate table and are
not included in transaction input features.

### V2 Generation and Validation Commands

From the project root:

Generate a full V2 dataset:

`python backend/generate_configurable_v2.py --users 1000 --transactions-per-user 500 --output-dir backend/v2_full_run1`

Validate:

`python backend/validate_full_dataset_v2.py --dataset-dir backend/v2_full_run1 --transactions-per-user 500`

Evaluate categorization:

`python backend/evaluate_categorization_v2.py`

Evaluate recurring integrity:

`python backend/evaluate_recurring_v2.py`

Export JSON:

`python backend/export_v2_json.py`

Export SQL:

`python backend/export_v2_sql.py`


### Labelled Recurring Evaluation

See ackend/dataset_exports/v2_recurring_labelled_evaluation_report.json for group-level metrics and documented limitations.

### Final V2 Validation

See ackend/dataset_exports/v2_final_validation_report.json for the final 500,000-transaction validation result.

# PennyWise V2 — Data Lifecycle and Validation

## 1. Dataset Scope

- Synthetic users: 1,000
- Accounts: 2,000
- Transactions: 500,000
- Monthly budgets: 60,000
- Recurring series: 3,000
- Recurring occurrences: 36,000
- Generation seed: 20261022
- Dataset period: 2025-11-10 to 2026-11-09

## 2. Entity Relationships

| Parent | Child | Relationship |
|---|---|---|
| UserProfile | Account | One-to-many |
| UserProfile | Transaction | One-to-many |
| Account | Transaction | One-to-many |
| Merchant | Transaction | One-to-many; merchant may be optional |
| Category | Transaction | One-to-many; category may be optional |
| UserProfile | Budget | One-to-many |
| Category | Budget | One-to-many |
| UserProfile | RecurringSeries | One-to-many |
| RecurringSeries | RecurringOccurrence | One-to-many |
| Transaction | RecurringOccurrence | Referenced transaction |

Identifiers are stored explicitly. Dependent records must reference valid parent IDs.

## 3. Transaction Lifecycle

1. Generate user, account, merchant and category reference data.
2. Generate transactions with signed amounts.
3. Assign transaction type and completion status.
4. Apply categorization rules and retain ground-truth labels separately.
5. Link refunds to original expenses.
6. Pair internal transfers using transfer_group_id.
7. Associate recurring transactions with recurring occurrences.
8. Aggregate monthly budget spending and financial insights.

### Signed Amount Rules

| Type | Amount |
|---|---|
| Expense | Negative |
| Income | Positive |
| Refund | Positive |
| Transfer outgoing | Negative |
| Transfer incoming | Positive |

Refunds reduce net spending. Internal transfers do not count as household spending.

## 4. Budget Lifecycle

Budgets reference a valid user and category and define a period_start and period_end.

Budget utilization is derived from eligible expenses and refunds during the applicable period. Transfers are excluded.

Unknown category references must be rejected by validation.

## 5. Recurring Payment Lifecycle

1. Identify candidate transactions.
2. Group by account, transaction type, merchant, normalized description and amount.
3. Require at least three occurrences for the revised detector.
4. Check frequency and interval consistency.
5. Create or reuse recurring series.
6. Link matching transactions as occurrences.
7. Calculate the next expected payment date.
8. Identify overdue or missing payments when applicable.

The live API currently operates on the local application database. The V2 CSV evaluation is separate.

## 6. Edge Cases

Five labelled negative-case fixtures are documented in:

backend/dataset_exports/v2_edge_case_ground_truth.csv

The cases cover:

- Transfer double counting
- Refund incorrectly treated as expense
- Skipped recurring payment
- Timezone calendar-date boundary
- Invalid budget category

These fixtures are separate from the immutable V2 transaction dataset. They are not claims that corrupted rows were inserted into the baseline.

## 7. Validation and Reconciliation

V2 validation covers primary-key uniqueness, foreign-key references, transaction integrity, refunds, transfers, recurring relationships and date consistency.

Ledger reconciliation independently verifies:

- Signed income and expenses
- Refund-adjusted net spending
- Transfer pair balance
- Account balance changes
- Net cashflow arithmetic

Report:

backend/dataset_exports/v2_ledger_reconciliation_report.json

Opening bank balances are not independently reconciled by this report.

## 8. Evaluation and Limitations

Categorization and recurring evaluation reports are stored in backend/dataset_exports.

The V2 recurring offline group-level evaluation reported:

- TP: 2,999
- FP: 0
- FN: 1
- TN: 393,530
- Precision: 100%
- Recall: 99.9667%
- F1: 99.9833%

These results use generator-produced reference labels. They are not independently human-annotated and do not measure production performance.

Exact/rounded amount grouping may miss subscriptions whose amounts vary.

The Flask endpoint has been smoke-tested against the local demo database; this does not establish equivalent V2 or production accuracy.

## 9. Traceability and History

Original V2 CSVs are preserved for reproducibility.

Ground-truth labels, validation reports, evaluation reports and edge-case fixtures are stored separately.

Transaction, recurring and budget records contain lifecycle/status information. A complete append-only event history for every state transition has not been independently verified; status fields alone should not be represented as full event sourcing.

## 10. Reproducibility

Two full V2 runs were previously compared across ten baseline CSV files with matching SHA-256 hashes.

Subsequent generator changes, including category-rule export, require a separate reproducibility verification before claiming identical output from the latest generator version.

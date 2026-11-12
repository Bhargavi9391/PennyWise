# PennyWise V2 ? Detailed Data Dictionary

Source: `backend/generate_configurable_v2.py` and baseline V2 CSV exports.

Types and allowed values below describe the CSV contract and observed data.
They are not all enforced by database CHECK constraints.
Empty CSV strings represent missing optional values.
Monetary units are INR (?), with two decimal places.

## user_profiles

Rows inspected: 1,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| user_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| full_name | String | Yes | Text / identifier | Nonempty when required |
| email | String | Yes | Text / identifier | Nonempty when required |

## accounts

Rows inspected: 2,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| account_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| user_id | String | Yes | Text / identifier | Nonempty when required; references user_profiles.user_id |
| account_name | String | Yes | Text / identifier | Nonempty when required |
| account_type | String | Yes | Observed: Checking, Savings | Nonempty when required |

## merchants

Rows inspected: 21

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| merchant_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| merchant_name | String | Yes | Text / identifier | Nonempty when required |

## categories

Rows inspected: 7

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| category_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| category_name | String | Yes | Text / identifier | Nonempty when required |
| category_type | String | Yes | Observed: Expense, Income, Transfer | Nonempty when required |

## category_rules

Rows inspected: 28

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| rule_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| category_id | String | Yes | Text / identifier | Nonempty when required; references categories.category_id |
| rule_name | String | Yes | Text / identifier | Nonempty when required |
| match_field | String | Yes | Observed: description | Nonempty when required |
| match_type | String | Yes | Observed: contains | Nonempty when required |
| match_value | String | Yes | Text / identifier | Nonempty when required |
| priority | Integer | Yes | Count / priority | Integer |
| is_active | Boolean | Yes | 0 or 1 | Boolean representation |
| effective_from | Date | Yes | YYYY-MM-DD | Valid calendar date |
| effective_to | Date | No | YYYY-MM-DD | Valid calendar date |
| created_at | String | Yes | Text / identifier | Nonempty when required |

## transactions

Rows inspected: 500,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| transaction_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| user_id | String | Yes | Text / identifier | Nonempty when required; references user_profiles.user_id |
| account_id | String | Yes | Text / identifier | Nonempty when required; references accounts.account_id |
| merchant_id | String | No | Text / identifier | Nonempty when required; references merchants.merchant_id |
| category_id | String | No | Text / identifier | Nonempty when required; references categories.category_id |
| transaction_date | Date | Yes | YYYY-MM-DD | Valid calendar date |
| description | String | No | Text / identifier | Nonempty when required |
| amount | Decimal(12,2) | Yes | INR; 2 decimal places | Finite decimal; signed for transaction amount |
| transaction_type | String | Yes | Observed: Expense, Income, Refund, Transfer | Nonempty when required |
| status | String | Yes | Observed: Completed | Nonempty when required |
| original_transaction_id | String | No | Text / identifier | Nonempty when required |
| transfer_group_id | String | No | Text / identifier | Nonempty when required |

## ground_truth

Rows inspected: 500,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| transaction_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| expected_category_id | String | Yes | Text / identifier | Nonempty when required; references categories.category_id |
| expected_transaction_type | String | Yes | Observed: Expense, Income, Refund, Transfer | Nonempty when required |
| is_intentionally_uncategorized | Boolean | Yes | 0 or 1 | Boolean representation |
| issue_type | String | No | Observed: AMBIGUOUS_CATEGORY | Nonempty when required |
| original_transaction_id | String | No | Text / identifier | Nonempty when required; references transactions.transaction_id |
| transfer_group_id | String | No | Text / identifier | Nonempty when required |

## budgets

Rows inspected: 60,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| budget_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| user_id | String | Yes | Text / identifier | Nonempty when required; references user_profiles.user_id |
| category_id | String | Yes | Text / identifier | Nonempty when required; references categories.category_id |
| budget_amount | Decimal(12,2) | Yes | INR; 2 decimal places | Finite decimal; signed for transaction amount |
| period_start | Date | Yes | YYYY-MM-DD | Valid calendar date |
| period_end | Date | Yes | YYYY-MM-DD | Valid calendar date |
| status | String | Yes | Observed: Active | Nonempty when required |

## recurring_series

Rows inspected: 3,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| series_id | String | Yes | REC-000001 format | Primary key; globally unique; immutable |
| user_id | String | Yes | Text / identifier | Nonempty when required; references user_profiles.user_id |
| account_id | String | Yes | Text / identifier | Nonempty when required; references accounts.account_id |
| merchant_id | String | No | Text / identifier | Nonempty when required; references merchants.merchant_id |
| category_id | String | No | Text / identifier | Nonempty when required; references categories.category_id |
| series_name | String | Yes | Text / identifier | Nonempty when required |
| expected_amount | Decimal(12,2) | Yes | INR; 2 decimal places | Finite decimal; signed for transaction amount |
| frequency | String | Yes | Observed: Monthly | Nonempty when required |
| last_payment_date | Date | No | YYYY-MM-DD | Valid calendar date |
| next_payment_date | Date | Yes | YYYY-MM-DD | Valid calendar date |
| occurrence_count | Integer | Yes | Count / priority | Integer |
| status | String | Yes | Observed: Active | Nonempty when required |
## recurring_occurrences

Rows inspected: 36,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| occurrence_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| series_id | String | Yes | Text / identifier | Nonempty when required; references recurring_series.series_id |
| transaction_id | String | Yes | Text / identifier | Nonempty when required; references transactions.transaction_id |
| occurrence_date | Date | Yes | YYYY-MM-DD | Valid calendar date |
| actual_amount | Decimal(12,2) | Yes | INR; 2 decimal places | Finite decimal; signed for transaction amount |
| status | String | Yes | Observed: Matched | Nonempty when required |

## insights

Rows inspected: 1,000

| Field | Type | Required | Units / allowed values | Uniqueness / validation |
|---|---|---|---|---|
| insight_id | String | Yes | Text / identifier | Nonempty when required; primary key, unique |
| user_id | String | Yes | Text / identifier | Nonempty when required; references user_profiles.user_id |
| insight_type | String | Yes | Observed: Spending Summary | Nonempty when required |
| title | String | Yes | Text / identifier | Nonempty when required |
| description | String | Yes | Text / identifier | Nonempty when required |
| severity | String | Yes | Observed: Info | Nonempty when required |
| status | String | Yes | Observed: Active | Nonempty when required |
| created_date | Date | Yes | YYYY-MM-DD | Valid calendar date |

## Cross-record validation

- All primary keys must be unique.
- Foreign-key references must resolve to valid parent records.
- Account and transaction ownership must be consistent.
- Refund original_transaction_id must reference an eligible expense.
- Transfer groups must reconcile to zero.
- Budget period_start must not exceed period_end.
- Recurring occurrences must reference an existing recurring series and transaction.
- Category rules must have valid effective-date ordering.
- Ground truth must remain separate from model input features.

## Limitations

Observed values are not necessarily exhaustive allowed enums.
Required flags reflect the CSV schema and observed blanks, not always database constraints.
See `schema.sql` and `DATA_DICTIONARY.md` for operational database constraints.

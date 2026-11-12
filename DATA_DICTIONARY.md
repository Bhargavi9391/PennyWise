# PennyWise Data Dictionary

Generated from the actual SQLite database using PRAGMA metadata.

## accounts

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| account_id | VARCHAR(40) | Yes | No | - |
| user_id | VARCHAR(20) | No | No | user_profiles.user_id |
| account_name | VARCHAR(100) | No | No | - |
| account_type | VARCHAR(30) | No | No | - |
| created_at | DATETIME | No | Yes | - |

## budgets

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| budget_id | VARCHAR(60) | Yes | No | - |
| user_id | VARCHAR(20) | No | No | user_profiles.user_id |
| category_id | VARCHAR(30) | No | No | categories.category_id |
| budget_amount | NUMERIC(12, 2) | No | No | - |
| period_start | DATE | No | No | - |
| period_end | DATE | No | No | - |
| status | VARCHAR(20) | No | No | - |
| created_at | DATETIME | No | Yes | - |

## categories

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| category_id | VARCHAR(30) | Yes | No | - |
| category_name | VARCHAR(100) | No | No | - |
| category_type | VARCHAR(20) | No | No | - |

## category_rules

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| rule_id | VARCHAR(40) | Yes | No | - |
| category_id | VARCHAR(30) | No | No | categories.category_id |
| rule_name | VARCHAR(100) | No | No | - |
| match_field | VARCHAR(30) | No | No | - |
| match_type | VARCHAR(20) | No | No | - |
| match_value | VARCHAR(150) | No | No | - |
| priority | INTEGER | No | No | - |
| is_active | BOOLEAN | No | No | - |
| effective_from | DATE | No | No | - |
| effective_to | DATE | No | Yes | - |
| created_at | DATETIME | No | Yes | - |

## edge_case_scenarios

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| scenario_id | VARCHAR(50) | Yes | No | - |
| issue_type | VARCHAR(50) | No | No | - |
| title | VARCHAR(150) | No | No | - |
| related_transaction_id | VARCHAR(40) | No | Yes | transactions.transaction_id |
| related_series_id | VARCHAR(50) | No | Yes | recurring_series.series_id |
| observed_behavior | TEXT | No | No | - |
| expected_behavior | TEXT | No | No | - |
| test_payload | TEXT | No | No | - |
| severity | VARCHAR(20) | No | No | - |
| status | VARCHAR(20) | No | No | - |
| created_at | DATETIME | No | No | - |

## insights

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| insight_id | VARCHAR(50) | Yes | No | - |
| user_id | VARCHAR(20) | No | No | user_profiles.user_id |
| insight_type | VARCHAR(40) | No | No | - |
| severity | VARCHAR(20) | No | No | - |
| title | VARCHAR(150) | No | No | - |
| description | VARCHAR(500) | No | No | - |
| metric_value | NUMERIC(12, 2) | No | Yes | - |
| threshold_value | NUMERIC(12, 2) | No | Yes | - |
| category_id | VARCHAR(30) | No | Yes | categories.category_id |
| budget_id | VARCHAR(60) | No | Yes | budgets.budget_id |
| transaction_id | VARCHAR(40) | No | Yes | transactions.transaction_id |
| series_id | VARCHAR(50) | No | Yes | recurring_series.series_id |
| period_start | DATE | No | Yes | - |
| period_end | DATE | No | Yes | - |
| status | VARCHAR(20) | No | No | - |
| created_at | DATETIME | No | Yes | - |
| updated_at | DATETIME | No | Yes | - |

## merchants

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| merchant_id | VARCHAR(30) | Yes | No | - |
| merchant_name | VARCHAR(150) | No | No | - |
| created_at | DATETIME | No | Yes | - |

## recurring_occurrences

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| occurrence_id | VARCHAR(50) | Yes | No | - |
| series_id | VARCHAR(50) | No | No | recurring_series.series_id |
| transaction_id | VARCHAR(40) | No | No | transactions.transaction_id |
| occurrence_date | DATE | No | No | - |
| actual_amount | NUMERIC(12, 2) | No | No | - |
| status | VARCHAR(20) | No | No | - |
| created_at | DATETIME | No | Yes | - |

## recurring_series

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| series_id | VARCHAR(50) | Yes | No | - |
| user_id | VARCHAR(20) | No | No | user_profiles.user_id |
| account_id | VARCHAR(40) | No | No | accounts.account_id |
| merchant_id | VARCHAR(30) | No | Yes | merchants.merchant_id |
| category_id | VARCHAR(30) | No | Yes | categories.category_id |
| series_name | VARCHAR(150) | No | No | - |
| expected_amount | NUMERIC(12, 2) | No | No | - |
| frequency | VARCHAR(20) | No | No | - |
| last_payment_date | DATE | No | Yes | - |
| next_payment_date | DATE | No | No | - |
| occurrence_count | INTEGER | No | No | - |
| status | VARCHAR(20) | No | No | - |
| created_at | DATETIME | No | Yes | - |
| updated_at | DATETIME | No | Yes | - |

## transaction_categorizations

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| decision_id | VARCHAR(50) | Yes | No | - |
| transaction_id | VARCHAR(40) | No | No | transactions.transaction_id |
| rule_id | VARCHAR(40) | No | Yes | category_rules.rule_id |
| category_id | VARCHAR(30) | No | No | categories.category_id |
| matched_field | VARCHAR(30) | No | Yes | - |
| matched_value | VARCHAR(150) | No | Yes | - |
| decision_method | VARCHAR(30) | No | No | - |
| created_at | DATETIME | No | Yes | - |

## transactions

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| transaction_id | VARCHAR(40) | Yes | No | - |
| user_id | VARCHAR(20) | No | No | user_profiles.user_id |
| account_id | VARCHAR(40) | No | No | accounts.account_id |
| merchant_id | VARCHAR(30) | No | Yes | merchants.merchant_id |
| category_id | VARCHAR(30) | No | Yes | categories.category_id |
| transaction_date | DATE | No | No | - |
| description | VARCHAR(250) | No | Yes | - |
| amount | NUMERIC(12, 2) | No | No | - |
| transaction_type | VARCHAR(20) | No | No | - |
| status | VARCHAR(20) | No | Yes | - |
| original_transaction_id | VARCHAR(40) | No | Yes | transactions.transaction_id |
| transfer_group_id | VARCHAR(40) | No | Yes | - |
| created_at | DATETIME | No | Yes | - |

## user_profiles

| Column | Data type | Primary key | Nullable | Foreign key |
|---|---|---|---|---|
| user_id | VARCHAR(20) | Yes | No | - |
| full_name | VARCHAR(100) | No | No | - |
| email | VARCHAR(150) | No | No | - |
| created_at | DATETIME | No | Yes | - |


---

# Operational Database ? Audit History

## lifecycle_events (Operational Database)

Stores immutable audit records for transaction lifecycle actions and recurring-series status changes. This table belongs to the operational application database, not the synthetic dataset schema.

| Column | Type | Required | Description / Validation |
|---|---|---|---|
| event_id | VARCHAR(60) | Yes | Primary key; unique event identifier |
| entity_type | VARCHAR(40) | Yes | Transaction, RecurringSeries, Budget, or Insight |
| entity_id | VARCHAR(60) | Yes | ID of the affected entity; polymorphic reference, not a direct foreign key |
| event_type | VARCHAR(40) | Yes | Created, Updated, Status Changed, or Deleted |
| old_value | VARCHAR(500) | No | Previous entity values or status |
| new_value | VARCHAR(500) | No | New entity values or status |
| actor | VARCHAR(100) | Yes | Actor responsible for the event; defaults to system |
| reason | VARCHAR(500) | No | Explanation for the event |
| event_timestamp | DATETIME | Yes | UTC event timestamp; defaults to creation time |

**Indexes:** `(entity_type, entity_id)` and `event_timestamp`.

**Traceability:** Events retain previous and new values. Deletion events remain available after the original entity is deleted.

**API:** `GET /api/lifecycle-events` supports `entity_type`, `entity_id`, and `limit` query parameters. Limit range: 1?100; default: 50.

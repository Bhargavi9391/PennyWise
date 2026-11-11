# PennyWise Entity Relationship Diagram

Relationships below are derived from the SQLite foreign-key definitions.

```mermaid
erDiagram
    accounts {
        VARCHAR(40) account_id PK
        VARCHAR(20) user_id
        VARCHAR(100) account_name
        VARCHAR(30) account_type
        DATETIME created_at
}
    budgets {
        VARCHAR(60) budget_id PK
        VARCHAR(20) user_id
        VARCHAR(30) category_id
        NUMERIC(12, 2) budget_amount
        DATE period_start
        DATE period_end
        VARCHAR(20) status
        DATETIME created_at
}
    categories {
        VARCHAR(30) category_id PK
        VARCHAR(100) category_name
        VARCHAR(20) category_type
}
    category_rules {
        VARCHAR(40) rule_id PK
        VARCHAR(30) category_id
        VARCHAR(100) rule_name
        VARCHAR(30) match_field
        VARCHAR(20) match_type
        VARCHAR(150) match_value
        INTEGER priority
        BOOLEAN is_active
        DATE effective_from
        DATE effective_to
        DATETIME created_at
}
    edge_case_scenarios {
        VARCHAR(50) scenario_id PK
        VARCHAR(50) issue_type
        VARCHAR(150) title
        VARCHAR(40) related_transaction_id
        VARCHAR(50) related_series_id
        TEXT observed_behavior
        TEXT expected_behavior
        TEXT test_payload
        VARCHAR(20) severity
        VARCHAR(20) status
        DATETIME created_at
}
    insights {
        VARCHAR(50) insight_id PK
        VARCHAR(20) user_id
        VARCHAR(40) insight_type
        VARCHAR(20) severity
        VARCHAR(150) title
        VARCHAR(500) description
        NUMERIC(12, 2) metric_value
        NUMERIC(12, 2) threshold_value
        VARCHAR(30) category_id
        VARCHAR(60) budget_id
        VARCHAR(40) transaction_id
        VARCHAR(50) series_id
        DATE period_start
        DATE period_end
        VARCHAR(20) status
        DATETIME created_at
        DATETIME updated_at
}
    merchants {
        VARCHAR(30) merchant_id PK
        VARCHAR(150) merchant_name
        DATETIME created_at
}
    recurring_occurrences {
        VARCHAR(50) occurrence_id PK
        VARCHAR(50) series_id
        VARCHAR(40) transaction_id
        DATE occurrence_date
        NUMERIC(12, 2) actual_amount
        VARCHAR(20) status
        DATETIME created_at
}
    recurring_series {
        VARCHAR(50) series_id PK
        VARCHAR(20) user_id
        VARCHAR(40) account_id
        VARCHAR(30) merchant_id
        VARCHAR(30) category_id
        VARCHAR(150) series_name
        NUMERIC(12, 2) expected_amount
        VARCHAR(20) frequency
        DATE last_payment_date
        DATE next_payment_date
        INTEGER occurrence_count
        VARCHAR(20) status
        DATETIME created_at
        DATETIME updated_at
}
    transaction_categorizations {
        VARCHAR(50) decision_id PK
        VARCHAR(40) transaction_id
        VARCHAR(40) rule_id
        VARCHAR(30) category_id
        VARCHAR(30) matched_field
        VARCHAR(150) matched_value
        VARCHAR(30) decision_method
        DATETIME created_at
}
    transactions {
        VARCHAR(40) transaction_id PK
        VARCHAR(20) user_id
        VARCHAR(40) account_id
        VARCHAR(30) merchant_id
        VARCHAR(30) category_id
        DATE transaction_date
        VARCHAR(250) description
        NUMERIC(12, 2) amount
        VARCHAR(20) transaction_type
        VARCHAR(20) status
        VARCHAR(40) original_transaction_id
        VARCHAR(40) transfer_group_id
        DATETIME created_at
}
    user_profiles {
        VARCHAR(20) user_id PK
        VARCHAR(100) full_name
        VARCHAR(150) email
        DATETIME created_at
}
    user_profiles ||--o{ accounts : "user_id"
    categories ||--o{ budgets : "category_id"
    user_profiles ||--o{ budgets : "user_id"
    categories ||--o{ category_rules : "category_id"
    recurring_series ||--o{ edge_case_scenarios : "related_series_id"
    transactions ||--o{ edge_case_scenarios : "related_transaction_id"
    recurring_series ||--o{ insights : "series_id"
    transactions ||--o{ insights : "transaction_id"
    budgets ||--o{ insights : "budget_id"
    categories ||--o{ insights : "category_id"
    user_profiles ||--o{ insights : "user_id"
    transactions ||--o{ recurring_occurrences : "transaction_id"
    recurring_series ||--o{ recurring_occurrences : "series_id"
    categories ||--o{ recurring_series : "category_id"
    merchants ||--o{ recurring_series : "merchant_id"
    accounts ||--o{ recurring_series : "account_id"
    user_profiles ||--o{ recurring_series : "user_id"
    categories ||--o{ transaction_categorizations : "category_id"
    category_rules ||--o{ transaction_categorizations : "rule_id"
    transactions ||--o{ transaction_categorizations : "transaction_id"
    transactions ||--o{ transactions : "original_transaction_id"
    categories ||--o{ transactions : "category_id"
    merchants ||--o{ transactions : "merchant_id"
    accounts ||--o{ transactions : "account_id"
    user_profiles ||--o{ transactions : "user_id"
```

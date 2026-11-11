CREATE INDEX idx_refund_match ON transactions(user_id,merchant_id,transaction_type,transaction_date);

CREATE TABLE accounts (
	account_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(20) NOT NULL, 
	account_name VARCHAR(100) NOT NULL, 
	account_type VARCHAR(30) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (account_id), 
	FOREIGN KEY(user_id) REFERENCES user_profiles (user_id)
);

CREATE TABLE budgets (
	budget_id VARCHAR(60) NOT NULL, 
	user_id VARCHAR(20) NOT NULL, 
	category_id VARCHAR(30) NOT NULL, 
	budget_amount NUMERIC(12, 2) NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (budget_id), 
	CONSTRAINT check_positive_budget CHECK (budget_amount > 0), 
	CONSTRAINT check_budget_period CHECK (period_end >= period_start), 
	CONSTRAINT check_budget_status CHECK (status IN ('Active', 'Inactive')), 
	CONSTRAINT unique_user_category_budget_period UNIQUE (user_id, category_id, period_start, period_end), 
	FOREIGN KEY(user_id) REFERENCES user_profiles (user_id), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id)
);

CREATE TABLE categories (
	category_id VARCHAR(30) NOT NULL, 
	category_name VARCHAR(100) NOT NULL, 
	category_type VARCHAR(20) NOT NULL, 
	PRIMARY KEY (category_id), 
	CONSTRAINT check_category_type CHECK (category_type IN ('Income', 'Expense', 'Transfer')), 
	UNIQUE (category_name)
);

CREATE TABLE category_rules (
	rule_id VARCHAR(40) NOT NULL, 
	category_id VARCHAR(30) NOT NULL, 
	rule_name VARCHAR(100) NOT NULL, 
	match_field VARCHAR(30) NOT NULL, 
	match_type VARCHAR(20) NOT NULL, 
	match_value VARCHAR(150) NOT NULL, 
	priority INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	created_at DATETIME, 
	PRIMARY KEY (rule_id), 
	CONSTRAINT check_rule_match_field CHECK (match_field IN ('description', 'merchant')), 
	CONSTRAINT check_rule_match_type CHECK (match_type IN ('contains', 'exact', 'starts_with')), 
	CONSTRAINT check_rule_priority CHECK (priority >= 1), 
	CONSTRAINT check_rule_effective_dates CHECK (effective_to IS NULL OR effective_to >= effective_from), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id)
);

CREATE TABLE edge_case_scenarios (
    scenario_id VARCHAR(50) PRIMARY KEY,
    issue_type VARCHAR(50) NOT NULL,
    title VARCHAR(150) NOT NULL,
    related_transaction_id VARCHAR(40),
    related_series_id VARCHAR(50),
    observed_behavior TEXT NOT NULL,
    expected_behavior TEXT NOT NULL,
    test_payload TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (related_transaction_id)
        REFERENCES transactions(transaction_id),
    FOREIGN KEY (related_series_id)
        REFERENCES recurring_series(series_id)
);

CREATE TABLE insights (
	insight_id VARCHAR(50) NOT NULL, 
	user_id VARCHAR(20) NOT NULL, 
	insight_type VARCHAR(40) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	metric_value NUMERIC(12, 2), 
	threshold_value NUMERIC(12, 2), 
	category_id VARCHAR(30), 
	budget_id VARCHAR(60), 
	transaction_id VARCHAR(40), 
	series_id VARCHAR(50), 
	period_start DATE, 
	period_end DATE, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (insight_id), 
	CONSTRAINT check_insight_type CHECK (insight_type IN ('Budget Overspending', 'Budget Warning', 'Spending Increase', 'Recurring Payment', 'Uncategorized Transaction')), 
	CONSTRAINT check_insight_severity CHECK (severity IN ('Low', 'Medium', 'High')), 
	CONSTRAINT check_insight_status CHECK (status IN ('New', 'Acknowledged', 'Resolved')), 
	CONSTRAINT check_insight_period CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start), 
	FOREIGN KEY(user_id) REFERENCES user_profiles (user_id), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id), 
	FOREIGN KEY(budget_id) REFERENCES budgets (budget_id), 
	FOREIGN KEY(transaction_id) REFERENCES transactions (transaction_id), 
	FOREIGN KEY(series_id) REFERENCES recurring_series (series_id)
);

CREATE TABLE merchants (
	merchant_id VARCHAR(30) NOT NULL, 
	merchant_name VARCHAR(150) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (merchant_id)
);

CREATE TABLE recurring_occurrences (
	occurrence_id VARCHAR(50) NOT NULL, 
	series_id VARCHAR(50) NOT NULL, 
	transaction_id VARCHAR(40) NOT NULL, 
	occurrence_date DATE NOT NULL, 
	actual_amount NUMERIC(12, 2) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (occurrence_id), 
	CONSTRAINT check_occurrence_positive_amount CHECK (actual_amount > 0), 
	CONSTRAINT check_occurrence_status CHECK (status IN ('Matched', 'Amount Mismatch', 'Reviewed')), 
	CONSTRAINT unique_recurring_transaction UNIQUE (series_id, transaction_id), 
	FOREIGN KEY(series_id) REFERENCES recurring_series (series_id), 
	FOREIGN KEY(transaction_id) REFERENCES transactions (transaction_id)
);

CREATE TABLE recurring_series (
	series_id VARCHAR(50) NOT NULL, 
	user_id VARCHAR(20) NOT NULL, 
	account_id VARCHAR(40) NOT NULL, 
	merchant_id VARCHAR(30), 
	category_id VARCHAR(30), 
	series_name VARCHAR(150) NOT NULL, 
	expected_amount NUMERIC(12, 2) NOT NULL, 
	frequency VARCHAR(20) NOT NULL, 
	last_payment_date DATE, 
	next_payment_date DATE NOT NULL, 
	occurrence_count INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (series_id), 
	CONSTRAINT check_recurring_positive_amount CHECK (expected_amount > 0), 
	CONSTRAINT check_recurring_frequency CHECK (frequency IN ('Weekly', 'Monthly', 'Quarterly', 'Yearly')), 
	CONSTRAINT check_recurring_status CHECK (status IN ('Active', 'Paused', 'Completed', 'Needs Review')), 
	CONSTRAINT check_recurring_occurrence_count CHECK (occurrence_count >= 0), 
	FOREIGN KEY(user_id) REFERENCES user_profiles (user_id), 
	FOREIGN KEY(account_id) REFERENCES accounts (account_id), 
	FOREIGN KEY(merchant_id) REFERENCES merchants (merchant_id), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id)
);

CREATE TABLE transaction_categorizations (
	decision_id VARCHAR(50) NOT NULL, 
	transaction_id VARCHAR(40) NOT NULL, 
	rule_id VARCHAR(40), 
	category_id VARCHAR(30) NOT NULL, 
	matched_field VARCHAR(30), 
	matched_value VARCHAR(150), 
	decision_method VARCHAR(30) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (decision_id), 
	FOREIGN KEY(transaction_id) REFERENCES transactions (transaction_id), 
	FOREIGN KEY(rule_id) REFERENCES category_rules (rule_id), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id)
);

CREATE TABLE transactions (
	transaction_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(20) NOT NULL, 
	account_id VARCHAR(40) NOT NULL, 
	merchant_id VARCHAR(30), 
	category_id VARCHAR(30), 
	transaction_date DATE NOT NULL, 
	description VARCHAR(250), 
	amount NUMERIC(12, 2) NOT NULL, 
	transaction_type VARCHAR(20) NOT NULL, 
	status VARCHAR(20), 
	original_transaction_id VARCHAR(40), 
	transfer_group_id VARCHAR(40), 
	created_at DATETIME, 
	PRIMARY KEY (transaction_id), 
	CONSTRAINT check_positive_amount CHECK (amount > 0), 
	CONSTRAINT check_transaction_type CHECK (transaction_type IN ('Income', 'Expense', 'Transfer', 'Refund')), 
	CONSTRAINT check_transaction_status CHECK (status IN ('Pending', 'Completed', 'Failed', 'Reversed')), 
	FOREIGN KEY(user_id) REFERENCES user_profiles (user_id), 
	FOREIGN KEY(account_id) REFERENCES accounts (account_id), 
	FOREIGN KEY(merchant_id) REFERENCES merchants (merchant_id), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id), 
	FOREIGN KEY(original_transaction_id) REFERENCES transactions (transaction_id)
);

CREATE TABLE user_profiles (
	user_id VARCHAR(20) NOT NULL, 
	full_name VARCHAR(100) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (user_id), 
	UNIQUE (email)
);

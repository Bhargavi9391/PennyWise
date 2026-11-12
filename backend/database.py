
from pathlib import Path
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Date,
    Numeric,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Integer,
    Boolean,
)

from sqlalchemy.orm import declarative_base, relationship, sessionmaker


# =====================================
# DATABASE CONFIGURATION
# =====================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'pennywise.db'}"

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


# =====================================
# 1. USER PROFILE
# =====================================

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(20), primary_key=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("Account", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    recurring_series = relationship("RecurringSeries", back_populates="user")


# =====================================
# 2. ACCOUNT
# =====================================

class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(40), primary_key=True)

    user_id = Column(
        String(20),
        ForeignKey("user_profiles.user_id"),
        nullable=False
    )

    account_name = Column(String(100), nullable=False)
    account_type = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserProfile", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    recurring_series = relationship("RecurringSeries", back_populates="account")


# =====================================
# 3. MERCHANT
# =====================================

class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(30), primary_key=True)
    merchant_name = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="merchant")
    recurring_series = relationship("RecurringSeries", back_populates="merchant")


# =====================================
# 4. CATEGORY
# =====================================

class Category(Base):
    __tablename__ = "categories"

    category_id = Column(String(30), primary_key=True)
    category_name = Column(String(100), unique=True, nullable=False)
    category_type = Column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category_type IN ('Income', 'Expense', 'Transfer')",
            name="check_category_type"
        ),
    )

    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")
    rules = relationship("CategoryRule", back_populates="category")
    recurring_series = relationship("RecurringSeries", back_populates="category")


# =====================================
# 5. BUDGET
# =====================================

class Budget(Base):
    __tablename__ = "budgets"

    budget_id = Column(String(60), primary_key=True)

    user_id = Column(
        String(20),
        ForeignKey("user_profiles.user_id"),
        nullable=False
    )

    category_id = Column(
        String(30),
        ForeignKey("categories.category_id"),
        nullable=False
    )

    budget_amount = Column(Numeric(12, 2), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    status = Column(String(20), default="Active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("budget_amount > 0", name="check_positive_budget"),
        CheckConstraint("period_end >= period_start", name="check_budget_period"),
        CheckConstraint(
            "status IN ('Active', 'Inactive')",
            name="check_budget_status"
        ),
        UniqueConstraint(
            "user_id",
            "category_id",
            "period_start",
            "period_end",
            name="unique_user_category_budget_period"
        )
    )

    category = relationship("Category", back_populates="budgets")


# =====================================
# 6. CATEGORY RULE
# =====================================

class CategoryRule(Base):
    __tablename__ = "category_rules"

    rule_id = Column(String(40), primary_key=True)

    category_id = Column(
        String(30),
        ForeignKey("categories.category_id"),
        nullable=False
    )

    rule_name = Column(String(100), nullable=False)
    match_field = Column(String(30), default="description", nullable=False)
    match_type = Column(String(20), default="contains", nullable=False)
    match_value = Column(String(150), nullable=False)

    priority = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "match_field IN ('description', 'merchant')",
            name="check_rule_match_field"
        ),
        CheckConstraint(
            "match_type IN ('contains', 'exact', 'starts_with')",
            name="check_rule_match_type"
        ),
        CheckConstraint("priority >= 1", name="check_rule_priority"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="check_rule_effective_dates"
        ),
    )

    category = relationship("Category", back_populates="rules")
    decisions = relationship(
        "TransactionCategorization",
        back_populates="rule"
    )


# =====================================
# 7. TRANSACTION
# =====================================

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(40), primary_key=True)

    user_id = Column(
        String(20),
        ForeignKey("user_profiles.user_id"),
        nullable=False
    )

    account_id = Column(
        String(40),
        ForeignKey("accounts.account_id"),
        nullable=False
    )

    merchant_id = Column(
        String(30),
        ForeignKey("merchants.merchant_id"),
        nullable=True
    )

    category_id = Column(
        String(30),
        ForeignKey("categories.category_id"),
        nullable=True
    )

    transaction_date = Column(Date, nullable=False)
    description = Column(String(250))
    amount = Column(Numeric(12, 2), nullable=False)

    transaction_type = Column(String(20), nullable=False)
    status = Column(String(20), default="Completed")

    original_transaction_id = Column(
        String(40),
        ForeignKey("transactions.transaction_id"),
        nullable=True
    )

    transfer_group_id = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_positive_amount"),
        CheckConstraint(
            "transaction_type IN ('Income', 'Expense', 'Transfer', 'Refund')",
            name="check_transaction_type"
        ),
        CheckConstraint(
            "status IN ('Pending', 'Completed', 'Failed', 'Reversed')",
            name="check_transaction_status"
        ),
    )

    user = relationship("UserProfile", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    original_transaction = relationship(
        "Transaction",
        remote_side=[transaction_id]
    )

    categorizations = relationship(
        "TransactionCategorization",
        back_populates="transaction"
    )

    recurring_occurrences = relationship(
        "RecurringOccurrence",
        back_populates="transaction"
    )


# =====================================
# 8. TRANSACTION CATEGORIZATION HISTORY
# =====================================

class TransactionCategorization(Base):
    __tablename__ = "transaction_categorizations"

    decision_id = Column(String(50), primary_key=True)

    transaction_id = Column(
        String(40),
        ForeignKey("transactions.transaction_id"),
        nullable=False
    )

    rule_id = Column(
        String(40),
        ForeignKey("category_rules.rule_id"),
        nullable=True
    )

    category_id = Column(
        String(30),
        ForeignKey("categories.category_id"),
        nullable=False
    )

    matched_field = Column(String(30), nullable=True)
    matched_value = Column(String(150), nullable=True)

    decision_method = Column(String(30), default="manual", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship(
        "Transaction",
        back_populates="categorizations"
    )

    rule = relationship(
        "CategoryRule",
        back_populates="decisions"
    )


# =====================================
# 9. RECURRING SERIES
# =====================================

class RecurringSeries(Base):
    __tablename__ = "recurring_series"

    series_id = Column(String(50), primary_key=True)

    user_id = Column(
        String(20),
        ForeignKey("user_profiles.user_id"),
        nullable=False
    )

    account_id = Column(
        String(40),
        ForeignKey("accounts.account_id"),
        nullable=False
    )

    merchant_id = Column(
        String(30),
        ForeignKey("merchants.merchant_id"),
        nullable=True
    )

    category_id = Column(
        String(30),
        ForeignKey("categories.category_id"),
        nullable=True
    )

    series_name = Column(String(150), nullable=False)

    expected_amount = Column(Numeric(12, 2), nullable=False)

    frequency = Column(String(20), nullable=False)

    last_payment_date = Column(Date, nullable=True)
    next_payment_date = Column(Date, nullable=False)

    occurrence_count = Column(Integer, default=0, nullable=False)

    status = Column(String(20), default="Active", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "expected_amount > 0",
            name="check_recurring_positive_amount"
        ),
        CheckConstraint(
            "frequency IN ('Weekly', 'Monthly', 'Quarterly', 'Yearly')",
            name="check_recurring_frequency"
        ),
        CheckConstraint(
            "status IN ('Active', 'Paused', 'Completed', 'Needs Review')",
            name="check_recurring_status"
        ),
        CheckConstraint(
            "occurrence_count >= 0",
            name="check_recurring_occurrence_count"
        ),
    )

    user = relationship("UserProfile", back_populates="recurring_series")
    account = relationship("Account", back_populates="recurring_series")
    merchant = relationship("Merchant", back_populates="recurring_series")
    category = relationship("Category", back_populates="recurring_series")

    occurrences = relationship(
        "RecurringOccurrence",
        back_populates="series"
    )


# =====================================
# 10. RECURRING OCCURRENCE
# =====================================

class RecurringOccurrence(Base):
    __tablename__ = "recurring_occurrences"

    occurrence_id = Column(String(50), primary_key=True)

    series_id = Column(
        String(50),
        ForeignKey("recurring_series.series_id"),
        nullable=False
    )

    transaction_id = Column(
        String(40),
        ForeignKey("transactions.transaction_id"),
        nullable=False
    )

    occurrence_date = Column(Date, nullable=False)
    actual_amount = Column(Numeric(12, 2), nullable=False)

    status = Column(String(20), default="Matched", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "actual_amount > 0",
            name="check_occurrence_positive_amount"
        ),
        CheckConstraint(
            "status IN ('Matched', 'Amount Mismatch', 'Reviewed')",
            name="check_occurrence_status"
        ),
        UniqueConstraint(
            "series_id",
            "transaction_id",
            name="unique_recurring_transaction"
        ),
    )

    series = relationship(
        "RecurringSeries",
        back_populates="occurrences"
    )

    transaction = relationship(
        "Transaction",
        back_populates="recurring_occurrences"
    )


# =====================================
# 11. INSIGHT
# =====================================

class Insight(Base):
    __tablename__ = "insights"

    insight_id = Column(String(50), primary_key=True)

    user_id = Column(
        String(20),
        ForeignKey("user_profiles.user_id"),
        nullable=False
    )

    insight_type = Column(String(40), nullable=False)
    severity = Column(String(20), default="Medium", nullable=False)

    title = Column(String(150), nullable=False)
    description = Column(String(500), nullable=False)

    metric_value = Column(Numeric(12, 2), nullable=True)
    threshold_value = Column(Numeric(12, 2), nullable=True)

    category_id = Column(
        String(30),
        ForeignKey("categories.category_id"),
        nullable=True
    )

    budget_id = Column(
        String(60),
        ForeignKey("budgets.budget_id"),
        nullable=True
    )

    transaction_id = Column(
        String(40),
        ForeignKey("transactions.transaction_id"),
        nullable=True
    )

    series_id = Column(
        String(50),
        ForeignKey("recurring_series.series_id"),
        nullable=True
    )

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    status = Column(String(20), default="New", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "insight_type IN ('Budget Overspending', 'Budget Warning', "
            "'Spending Increase', 'Recurring Payment', "
            "'Uncategorized Transaction')",
            name="check_insight_type"
        ),
        CheckConstraint(
            "severity IN ('Low', 'Medium', 'High')",
            name="check_insight_severity"
        ),
        CheckConstraint(
            "status IN ('New', 'Acknowledged', 'Resolved')",
            name="check_insight_status"
        ),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL "
            "OR period_end >= period_start",
            name="check_insight_period"
        ),
    )


# =====================================
# 12. LIFECYCLE EVENT HISTORY
# =====================================

class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"

    event_id = Column(String(60), primary_key=True)

    entity_type = Column(String(40), nullable=False)
    entity_id = Column(String(60), nullable=False)

    event_type = Column(String(40), nullable=False)

    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)

    actor = Column(String(100), nullable=False, default="system")
    reason = Column(String(500), nullable=True)

    event_timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('Transaction', 'RecurringSeries', 'Budget', 'Insight')",
            name="check_lifecycle_entity_type"
        ),
        CheckConstraint(
            "event_type IN ('Created', 'Updated', 'Status Changed', 'Deleted')",
            name="check_lifecycle_event_type"
        ),
    )



# =====================================
# CREATE DATABASE TABLES
# =====================================

def create_database():
    Base.metadata.create_all(bind=engine)
    print("PennyWise database tables created successfully!")


if __name__ == "__main__":
    create_database()

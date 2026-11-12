
from flask import Flask, jsonify, request
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import hashlib
import calendar
import re
import statistics
import uuid

from flask_cors import CORS

from database import (
    SessionLocal,
    Transaction,
    Category,
    Merchant,
    Budget,
    CategoryRule,
    TransactionCategorization,
    RecurringSeries,
    RecurringOccurrence,
    Insight,
    LifecycleEvent
)

app = Flask(__name__)
CORS(app)

DEMO_USER_ID = "USR-000001"
DEMO_ACCOUNT_ID = "ACC-USR-000001-01"


# =====================================
# DATE AND RECURRING HELPERS
# =====================================

def calculate_next_payment(last_date, frequency):
    """Calculate next payment date without invalid month dates."""

    if frequency == "Weekly":
        return last_date + timedelta(days=7)

    if frequency == "Monthly":
        year = last_date.year + (last_date.month // 12)
        month = last_date.month % 12 + 1
        day = min(last_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    if frequency == "Quarterly":
        year = last_date.year
        month = last_date.month + 3

        while month > 12:
            month -= 12
            year += 1

        day = min(last_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    if frequency == "Yearly":
        year = last_date.year + 1
        day = min(last_date.day, calendar.monthrange(year, last_date.month)[1])
        return date(year, last_date.month, day)

    return last_date

def calculate_payment_status(due_date, frequency, today=None):
    """
    Check whether a recurring payment is overdue.
    Keep the original due date unchanged.
    """
    today = today or date.today()

    if due_date >= today:
        return {
            "payment_status": "Upcoming",
            "days_overdue": 0,
            "due_date": due_date.isoformat(),
            "next_payment_date": due_date.isoformat()
        }

    days_overdue = (today - due_date).days
    next_date = due_date

    # Move forward until the next scheduled date is today or later.
    while next_date < today:
        next_date = calculate_next_payment(next_date, frequency)

        # Safety guard against an invalid or unsupported frequency.
        if next_date <= due_date and frequency not in [
            "Weekly", "Monthly", "Quarterly", "Yearly"
        ]:
            break

    return {
        "payment_status": "Overdue",
        "days_overdue": days_overdue,
        "due_date": due_date.isoformat(),
        "next_payment_date": next_date.isoformat()
    }

def identify_frequency(dates):
    """Identify a likely recurring frequency from transaction dates."""

    sorted_dates = sorted(dates)

    if len(sorted_dates) < 2:
        return None

    gaps = [
        (sorted_dates[index] - sorted_dates[index - 1]).days
        for index in range(1, len(sorted_dates))
    ]

    average_gap = statistics.mean(gaps)

    if 5 <= average_gap <= 9:
        return "Weekly"

    if 25 <= average_gap <= 35:
        return "Monthly"

    if 80 <= average_gap <= 100:
        return "Quarterly"

    if 350 <= average_gap <= 380:
        return "Yearly"

    return None


def normalize_description(description):
    """Normalize transaction descriptions for recurring detection."""

    value = (description or "").strip().lower()
    value = re.sub(r"\d+", "", value)
    value = re.sub(r"[^a-z\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def find_matching_rule(session, description, merchant_name, transaction_date):
    rules = session.query(CategoryRule).filter(
        CategoryRule.is_active.is_(True),
        CategoryRule.effective_from <= transaction_date
    ).order_by(
        CategoryRule.priority.asc(),
        CategoryRule.created_at.asc()
    ).all()

    for rule in rules:
        if rule.effective_to and rule.effective_to < transaction_date:
            continue

        source_text = (
            description or ""
            if rule.match_field == "description"
            else merchant_name or ""
        )

        source_text = source_text.strip().lower()
        match_value = rule.match_value.strip().lower()

        if rule.match_type == "contains":
            matched = match_value in source_text
        elif rule.match_type == "exact":
            matched = source_text == match_value
        else:
            matched = source_text.startswith(match_value)

        if matched:
            return rule

    return None


def save_categorization_history(
    session,
    transaction,
    category,
    rule=None,
    matched_field=None,
    matched_value=None,
    decision_method="manual"
):
    decision_id = (
        f"DEC-{transaction.transaction_id}-"
        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    )

    decision = TransactionCategorization(
        decision_id=decision_id,
        transaction_id=transaction.transaction_id,
        rule_id=rule.rule_id if rule else None,
        category_id=category.category_id,
        matched_field=matched_field,
        matched_value=matched_value,
        decision_method=decision_method
    )

    session.add(decision)


# =====================================
# HOME API
# =====================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "PennyWise Backend is Running!",
        "status": "success"
    })


# =====================================
# HEALTH API
# =====================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "application": "PennyWise",
        "backend": "Flask",
        "status": "healthy"
    })


# =====================================
# TRANSACTION APIs
# =====================================

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    session = SessionLocal()

    try:
        transactions = session.query(Transaction).filter(
            Transaction.user_id == DEMO_USER_ID
        ).order_by(Transaction.transaction_date.desc()).all()

        result = []

        for item in transactions:
            result.append({
                "transaction_id": item.transaction_id,
                "user_id": item.user_id,
                "account_id": item.account_id,
                "merchant_id": item.merchant_id,
                "merchant_name": item.merchant.merchant_name if item.merchant else None,
                "category_id": item.category_id,
                "category_name": item.category.category_name if item.category else None,
                "description": item.description,
                "amount": float(item.amount),
                "transaction_type": item.transaction_type,
                "status": item.status,
                "transaction_date": item.transaction_date.isoformat()
            })

        return jsonify({
            "status": "success",
            "total_transactions": len(result),
            "transactions": result
        })

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# GET CATEGORIES
# =====================================

@app.route("/api/categories", methods=["GET"])
def get_categories():
    session = SessionLocal()

    try:
        categories = session.query(Category).all()

        result = [{
            "category_id": item.category_id,
            "category_name": item.category_name,
            "category_type": item.category_type
        } for item in categories]

        return jsonify({
            "status": "success",
            "total_categories": len(result),
            "categories": result
        })

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# DASHBOARD
# =====================================


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    session = SessionLocal()

    try:
        today = date.today()
        month_start = today.replace(day=1)

        transactions = session.query(Transaction).filter(
            Transaction.user_id == DEMO_USER_ID,
            Transaction.status == "Completed",
            Transaction.transaction_date >= month_start,
            Transaction.transaction_date <= today
        ).all()

        income = sum(
            (Decimal(str(item.amount)) for item in transactions
             if item.transaction_type == "Income"),
            Decimal("0")
        )

        expenses = sum(
            (Decimal(str(item.amount)) for item in transactions
             if item.transaction_type == "Expense"),
            Decimal("0")
        )

        refunds = sum(
            (Decimal(str(item.amount)) for item in transactions
             if item.transaction_type == "Refund"),
            Decimal("0")
        )

        net_expenses = max(expenses - refunds, Decimal("0"))
        balance = income - net_expenses

        return jsonify({
            "status": "success",
            "period": "Current Month",
            "total_transactions": len(transactions),
            "total_income": float(income),
            "total_expenses": float(net_expenses),
            "gross_expenses": float(expenses),
            "total_refunds": float(refunds),
            "balance": float(balance)
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()



# =====================================
# ADD TRANSACTION
# =====================================

@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}

        required_fields = ["name", "amount", "date", "transaction_type"]

        if any(data.get(field) in (None, "") for field in required_fields):
            return jsonify({
                "status": "error",
                "message": "Name, amount, date and transaction type are required"
            }), 400

        try:
            amount = Decimal(str(data["amount"]))
            transaction_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid amount or date"}), 400

        if not amount.is_finite() or amount <= 0:
            return jsonify({"status": "error", "message": "Amount must be greater than zero"}), 400

        transaction_type = data["transaction_type"]

        if transaction_type not in ["Income", "Expense", "Transfer", "Refund"]:
            return jsonify({"status": "error", "message": "Invalid transaction type"}), 400

        category = None
        matched_rule = None

        if data.get("category"):
            category = session.query(Category).filter_by(
                category_name=data["category"]
            ).first()

            if not category:
                return jsonify({"status": "error", "message": "Category not found"}), 404
        else:
            matched_rule = find_matching_rule(
                session,
                data["name"],
                data.get("merchant_name"),
                transaction_date
            )

            if matched_rule:
                category = session.get(Category, matched_rule.category_id)

        year = transaction_date.year
        prefix = f"TXN-{year}-"

        # Include historical transaction IDs so deleted IDs are never reused.
        existing_ids = session.query(Transaction.transaction_id).filter(
            Transaction.transaction_id.like(f"{prefix}%")
        ).all()

        historical_ids = session.query(LifecycleEvent.entity_id).filter(
            LifecycleEvent.entity_type == "Transaction",
            LifecycleEvent.entity_id.like(f"{prefix}%")
        ).all()

        all_ids = [row[0] for row in existing_ids + historical_ids]

        numbers = [
            int(txn_id[len(prefix):])
            for txn_id in all_ids
            if txn_id.startswith(prefix) and txn_id[len(prefix):].isdigit()
        ]

        transaction_id = f"{prefix}{max(numbers, default=0) + 1:08d}"

        new_transaction = Transaction(
            transaction_id=transaction_id,
            user_id=DEMO_USER_ID,
            account_id=DEMO_ACCOUNT_ID,
            category_id=category.category_id if category else None,
            transaction_date=transaction_date,
            description=data["name"],
            amount=amount,
            transaction_type=transaction_type,
            status="Completed"
        )

        session.add(new_transaction)
        session.flush()

        if category:
            save_categorization_history(
                session,
                new_transaction,
                category,
                rule=matched_rule,
                matched_field=matched_rule.match_field if matched_rule else None,
                matched_value=matched_rule.match_value if matched_rule else None,
                decision_method="automatic" if matched_rule else "manual"
            )

        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Transaction",
            entity_id=transaction_id,
            event_type="Created",
            old_value=None,
            new_value=(
                f"type={transaction_type}; amount={amount}; "
                f"category_id={category.category_id if category else 'None'}; "
                f"status=Completed"
            ),
            actor="system",
            reason="Transaction created through API"
        ))

        session.commit()

        return jsonify({
            "status": "success",
            "message": "Transaction added successfully",
            "transaction_id": transaction_id,
            "category": category.category_name if category else None,
            "categorization_method": (
                "automatic" if matched_rule else
                "manual" if category else "uncategorized"
            ),
            "matched_rule": matched_rule.rule_name if matched_rule else None
        }), 201

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# UPDATE TRANSACTION
# =====================================

@app.route("/api/transactions/<transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}

        transaction = session.get(Transaction, transaction_id)

        if not transaction or transaction.user_id != DEMO_USER_ID:
            return jsonify({
                "status": "error",
                "message": "Transaction not found"
            }), 404

        # Capture original values before updating for audit history.
        old_snapshot = (
            f"name={transaction.description}; "
            f"amount={transaction.amount}; "
            f"date={transaction.transaction_date}; "
            f"type={transaction.transaction_type}; "
            f"category_id={transaction.category_id}"
        )

        # Keep existing values when fields are not provided
        name = data.get("name", transaction.description)
        amount_value = data.get("amount", transaction.amount)
        date_value = data.get(
            "date",
            transaction.transaction_date.strftime("%Y-%m-%d")
        )
        transaction_type = data.get(
            "transaction_type",
            transaction.transaction_type
        )

        if name in (None, ""):
            return jsonify({
                "status": "error",
                "message": "Transaction name is required"
            }), 400

        try:
            amount = Decimal(str(amount_value))
            transaction_date = datetime.strptime(
                str(date_value), "%Y-%m-%d"
            ).date()
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid amount or date"
            }), 400

        if not amount.is_finite() or amount <= 0:
            return jsonify({
                "status": "error",
                "message": "Amount must be greater than zero"
            }), 400

        if transaction_type not in [
            "Income", "Expense", "Transfer", "Refund"
        ]:
            return jsonify({
                "status": "error",
                "message": "Invalid transaction type"
            }), 400

        # Update category only when category information is supplied
        category = None
        matched_rule = None
        category_was_provided = (
            "category_id" in data or "category" in data
        )

        if category_was_provided:
            if data.get("category_id"):
                category = session.get(Category, data["category_id"])

            elif data.get("category"):
                category = session.query(Category).filter_by(
                    category_name=data["category"]
                ).first()

            else:
                category = None

            if (data.get("category_id") or data.get("category")) and not category:
                return jsonify({
                    "status": "error",
                    "message": "Category not found"
                }), 404

        # Save transaction fields
        transaction.description = name
        transaction.amount = amount
        transaction.transaction_date = transaction_date
        transaction.transaction_type = transaction_type

        if category_was_provided:
            transaction.category_id = (
                category.category_id if category else None
            )

            if category:
                save_categorization_history(
                    session,
                    transaction,
                    category,
                    rule=None,
                    matched_field=None,
                    matched_value=None,
                    decision_method="manual"
                )

        new_snapshot = (
            f"name={transaction.description}; "
            f"amount={transaction.amount}; "
            f"date={transaction.transaction_date}; "
            f"type={transaction.transaction_type}; "
            f"category_id={transaction.category_id}"
        )

        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Transaction",
            entity_id=transaction_id,
            event_type="Updated",
            old_value=old_snapshot,
            new_value=new_snapshot,
            actor="system",
            reason="Transaction updated through API"
        ))

        session.commit()

        return jsonify({
            "status": "success",
            "message": "Transaction updated successfully",
            "transaction_id": transaction.transaction_id,
            "category": category.category_name if category else (
                session.get(Category, transaction.category_id).category_name
                if transaction.category_id else None
            ),
            "categorization_method": (
                "manual" if category_was_provided and category
                else "uncategorized" if category_was_provided
                else "unchanged"
            )
        })

    except Exception as error:
        session.rollback()
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()


# =====================================
# DELETE TRANSACTION
# =====================================

@app.route("/api/transactions/<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    session = SessionLocal()

    try:
        transaction = session.get(Transaction, transaction_id)

        if not transaction or transaction.user_id != DEMO_USER_ID:
            return jsonify({"status": "error", "message": "Transaction not found"}), 404

        # Preserve referential integrity for recurring occurrences.
        occurrence_exists = session.query(RecurringOccurrence).filter_by(
            transaction_id=transaction_id
        ).first()

        if occurrence_exists:
            return jsonify({
                "status": "error",
                "message": "This transaction is linked to a recurring payment. Review the recurring payment first."
            }), 409

        linked_refund = session.query(Transaction).filter_by(
            original_transaction_id=transaction_id
        ).first()

        if linked_refund:
            return jsonify({
                "status": "error",
                "message": "This transaction has linked refunds. Review or resolve the refunds before deleting the original transaction."
            }), 409

        old_snapshot = (
            f"name={transaction.description}; "
            f"amount={transaction.amount}; "
            f"date={transaction.transaction_date}; "
            f"type={transaction.transaction_type}; "
            f"category_id={transaction.category_id}; "
            f"status={transaction.status}"
        )

        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Transaction",
            entity_id=transaction_id,
            event_type="Deleted",
            old_value=old_snapshot,
            new_value=None,
            actor="system",
            reason="Transaction deleted through API"
        ))

        session.query(TransactionCategorization).filter_by(
            transaction_id=transaction_id
        ).delete(synchronize_session=False)

        session.delete(transaction)
        session.commit()

        return jsonify({
            "status": "success",
            "message": "Transaction deleted successfully"
        })

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# BUDGET APIs
# =====================================

@app.route("/api/budgets", methods=["GET"])
def get_budgets():
    session = SessionLocal()

    try:
        budgets = (
            session.query(Budget)
            .filter(Budget.user_id == DEMO_USER_ID)
            .order_by(Budget.period_start.desc())
            .all()
        )

        budget_results = []

        for budget in budgets:
            # Load expenses and refunds in this budget period
            transactions = (
                session.query(Transaction)
                .filter(
                    Transaction.user_id == budget.user_id,
                    Transaction.transaction_date >= budget.period_start,
                    Transaction.transaction_date <= budget.period_end,
                    Transaction.status == "Completed",
                    Transaction.transaction_type.in_(["Expense", "Refund"])
                )
                .all()
            )

            gross_expenses = sum(
                float(tx.amount) for tx in transactions
                if tx.transaction_type == "Expense"
                and tx.category_id == budget.category_id
            )

            refund_original_ids = {
                tx.original_transaction_id for tx in transactions
                if tx.transaction_type == "Refund" and tx.original_transaction_id
            }
            original_categories = {}
            if refund_original_ids:
                original_categories = dict(
                    session.query(Transaction.transaction_id, Transaction.category_id)
                    .filter(
                        Transaction.user_id == budget.user_id,
                        Transaction.transaction_id.in_(refund_original_ids)
                    ).all()
                )

            total_refunds = sum(
                float(tx.amount) for tx in transactions
                if tx.transaction_type == "Refund"
                and original_categories.get(tx.original_transaction_id) == budget.category_id
            )

            # Refunds reduce spending in the original expense category
            actual_spending = max(gross_expenses - total_refunds, 0)

            budget_amount = float(budget.budget_amount)
            remaining_amount = budget_amount - actual_spending

            spending_percentage = (
                (actual_spending / budget_amount) * 100
                if budget_amount > 0 else 0
            )

            if actual_spending > budget_amount:
                budget_state = "Exceeded"
            else:
                budget_state = "Within Budget"

            category = session.query(Category).filter(
                Category.category_id == budget.category_id
            ).first()

            budget_results.append({
                "budget_id": budget.budget_id,
                "user_id": budget.user_id,
                "category_id": budget.category_id,
                "category": category.category_name if category else "Unknown",
                "budget_amount": budget_amount,
                "amount": budget_amount,
                "gross_expenses": round(gross_expenses, 2),
                "total_refunds": round(total_refunds, 2),
                "actual_spending": round(actual_spending, 2),
                "remaining_amount": round(remaining_amount, 2),
                "spending_percentage": round(spending_percentage, 2),
                "budget_state": budget_state,
                "is_over_budget": actual_spending > budget_amount,
                "period_start": budget.period_start.isoformat(),
                "period_end": budget.period_end.isoformat(),
                "status": budget.status
            })

        return jsonify({
            "status": "success",
            "total_budgets": len(budget_results),
            "budgets": budget_results
        }), 200

    except Exception as e:
        print("Get budgets error:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        session.close()

@app.route("/api/budgets", methods=["POST"])
def add_budget():
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}
        category_name = data.get("category")
        amount_value = data.get("amount")

        if not category_name or amount_value in (None, ""):
            return jsonify({"status": "error", "message": "Category and amount are required"}), 400

        try:
            amount = Decimal(str(amount_value))
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid budget amount"}), 400

        if not amount.is_finite() or amount <= 0:
            return jsonify({"status": "error", "message": "Budget amount must be positive"}), 400

        category = session.query(Category).filter_by(
            category_name=category_name,
            category_type="Expense"
        ).first()

        if not category:
            return jsonify({"status": "error", "message": "Expense category not found"}), 404

        today = date.today()
        period_start = today.replace(day=1)

        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        period_end = next_month - timedelta(days=1)

        existing = session.query(Budget).filter_by(
            user_id=DEMO_USER_ID,
            category_id=category.category_id,
            period_start=period_start,
            period_end=period_end
        ).first()

        if existing:
            old_budget_value = (
                f"amount={existing.budget_amount}; status={existing.status}"
            )
            existing.budget_amount = amount
            existing.status = "Active"
            budget = existing
            budget_event_type = "Updated"
            message = "Budget updated successfully"
        else:
            budget = Budget(
                budget_id=f"BUD-{DEMO_USER_ID}-{today.year}-{today.month:02d}-{category.category_id}",
                user_id=DEMO_USER_ID,
                category_id=category.category_id,
                budget_amount=amount,
                period_start=period_start,
                period_end=period_end,
                status="Active"
            )
            session.add(budget)
            old_budget_value = None
            budget_event_type = "Created"
            message = "Budget created successfully"

        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Budget",
            entity_id=budget.budget_id,
            event_type=budget_event_type,
            old_value=old_budget_value,
            new_value=(
                f"amount={amount}; status=Active; "
                f"category_id={category.category_id}"
            ),
            actor="system",
            reason="Budget saved through API"
        ))

        session.commit()

        return jsonify({
            "status": "success",
            "message": message,
            "budget_id": budget.budget_id
        }), 201

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


@app.route("/api/budgets/<budget_id>", methods=["PUT"])
def update_budget(budget_id):
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}
        budget = session.get(Budget, budget_id)

        if not budget or budget.user_id != DEMO_USER_ID:
            return jsonify({"status": "error", "message": "Budget not found"}), 404

        try:
            amount = Decimal(str(data.get("amount")))
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid budget amount"}), 400

        if not amount.is_finite() or amount <= 0:
            return jsonify({"status": "error", "message": "Budget amount must be positive"}), 400

        old_budget_value = (
            f"amount={budget.budget_amount}; status={budget.status}"
        )
        budget.budget_amount = amount

        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Budget",
            entity_id=budget.budget_id,
            event_type="Updated",
            old_value=old_budget_value,
            new_value=f"amount={amount}; status={budget.status}",
            actor="system",
            reason="Budget updated through API"
        ))

        session.commit()

        return jsonify({
            "status": "success",
            "message": "Budget updated successfully",
            "budget_id": budget.budget_id
        })

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


@app.route("/api/budgets/<budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    session = SessionLocal()

    try:
        budget = session.get(Budget, budget_id)

        if not budget or budget.user_id != DEMO_USER_ID:
            return jsonify({"status": "error", "message": "Budget not found"}), 404

        old_budget_value = (
            f"amount={budget.budget_amount}; status={budget.status}; "
            f"category_id={budget.category_id}; "
            f"period_start={budget.period_start}; "
            f"period_end={budget.period_end}"
        )

        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Budget",
            entity_id=budget.budget_id,
            event_type="Deleted",
            old_value=old_budget_value,
            new_value=None,
            actor="system",
            reason="Budget deleted through API"
        ))

        session.delete(budget)
        session.commit()

        return jsonify({
            "status": "success",
            "message": "Budget deleted successfully"
        })

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# CATEGORY RULE APIs
# =====================================

@app.route("/api/category-rules", methods=["GET"])
def get_category_rules():
    session = SessionLocal()

    try:
        rules = session.query(CategoryRule).order_by(CategoryRule.priority.asc()).all()

        result = [{
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "category_id": rule.category_id,
            "category": rule.category.category_name if rule.category else None,
            "match_field": rule.match_field,
            "match_type": rule.match_type,
            "match_value": rule.match_value,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "effective_from": rule.effective_from.isoformat(),
            "effective_to": rule.effective_to.isoformat() if rule.effective_to else None
        } for rule in rules]

        return jsonify({
            "status": "success",
            "total_rules": len(result),
            "rules": result
        })

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


@app.route("/api/category-rules", methods=["POST"])
def add_category_rule():
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}

        required_fields = [
            "rule_name", "category", "match_field", "match_type", "match_value"
        ]

        if any(not data.get(field) for field in required_fields):
            return jsonify({"status": "error", "message": "All rule fields are required"}), 400

        if data["match_field"] not in ["description", "merchant"]:
            return jsonify({"status": "error", "message": "Invalid match_field"}), 400

        if data["match_type"] not in ["contains", "exact", "starts_with"]:
            return jsonify({"status": "error", "message": "Invalid match_type"}), 400

        try:
            priority = int(data.get("priority", 100))
            effective_from = datetime.strptime(
                data.get("effective_from", date.today().isoformat()), "%Y-%m-%d"
            ).date()
            effective_to = (
                datetime.strptime(data["effective_to"], "%Y-%m-%d").date()
                if data.get("effective_to") else None
            )
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid priority or effective date"}), 400

        if priority < 1:
            return jsonify({"status": "error", "message": "Priority must be at least 1"}), 400

        if effective_to and effective_to < effective_from:
            return jsonify({"status": "error", "message": "End date cannot be before start date"}), 400

        category = session.query(Category).filter_by(
            category_name=data["category"],
            category_type="Expense"
        ).first()

        if not category:
            return jsonify({"status": "error", "message": "Expense category not found"}), 404

        rule_id = f"RULE-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        rule = CategoryRule(
            rule_id=rule_id,
            category_id=category.category_id,
            rule_name=data["rule_name"].strip(),
            match_field=data["match_field"],
            match_type=data["match_type"],
            match_value=data["match_value"].strip(),
            priority=priority,
            is_active=data.get("is_active", True),
            effective_from=effective_from,
            effective_to=effective_to
        )

        session.add(rule)
        session.commit()

        return jsonify({
            "status": "success",
            "message": "Category rule created successfully",
            "rule_id": rule_id
        }), 201

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


@app.route("/api/category-rules/<rule_id>", methods=["PUT"])
def update_category_rule(rule_id):
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}
        rule = session.get(CategoryRule, rule_id)

        if not rule:
            return jsonify({"status": "error", "message": "Category rule not found"}), 404

        if "rule_name" in data:
            rule.rule_name = data["rule_name"].strip()

        if "category" in data:
            category = session.query(Category).filter_by(
                category_name=data["category"],
                category_type="Expense"
            ).first()

            if not category:
                return jsonify({"status": "error", "message": "Expense category not found"}), 404

            rule.category_id = category.category_id

        if "match_field" in data:
            if data["match_field"] not in ["description", "merchant"]:
                return jsonify({"status": "error", "message": "Invalid match_field"}), 400
            rule.match_field = data["match_field"]

        if "match_type" in data:
            if data["match_type"] not in ["contains", "exact", "starts_with"]:
                return jsonify({"status": "error", "message": "Invalid match_type"}), 400
            rule.match_type = data["match_type"]

        if "match_value" in data:
            rule.match_value = data["match_value"].strip()

        if "priority" in data:
            try:
                priority = int(data["priority"])
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "Priority must be a number"}), 400

            if priority < 1:
                return jsonify({"status": "error", "message": "Priority must be at least 1"}), 400

            rule.priority = priority

        if "is_active" in data:
            if not isinstance(data["is_active"], bool):
                return jsonify({"status": "error", "message": "is_active must be true or false"}), 400
            rule.is_active = data["is_active"]

        try:
            if data.get("effective_from"):
                rule.effective_from = datetime.strptime(data["effective_from"], "%Y-%m-%d").date()

            if "effective_to" in data:
                rule.effective_to = (
                    datetime.strptime(data["effective_to"], "%Y-%m-%d").date()
                    if data["effective_to"] else None
                )
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid effective date"}), 400

        if rule.effective_to and rule.effective_to < rule.effective_from:
            return jsonify({"status": "error", "message": "End date cannot be before start date"}), 400

        session.commit()

        return jsonify({
            "status": "success",
            "message": "Category rule updated successfully",
            "rule_id": rule.rule_id
        })

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


@app.route("/api/category-rules/<rule_id>", methods=["DELETE"])
def delete_category_rule(rule_id):
    session = SessionLocal()

    try:
        rule = session.get(CategoryRule, rule_id)

        if not rule:
            return jsonify({"status": "error", "message": "Category rule not found"}), 404

        session.query(TransactionCategorization).filter_by(
            rule_id=rule_id
        ).update({"rule_id": None}, synchronize_session=False)

        session.delete(rule)
        session.commit()

        return jsonify({
            "status": "success",
            "message": "Category rule deleted successfully"
        })

    except Exception as error:
        session.rollback()
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# CATEGORIZATION HISTORY API
# =====================================

@app.route("/api/categorization-history", methods=["GET"])
def get_categorization_history():
    session = SessionLocal()

    try:
        decisions = session.query(TransactionCategorization).order_by(
            TransactionCategorization.created_at.desc()
        ).all()

        result = []

        for item in decisions:
            category = session.get(Category, item.category_id)

            result.append({
                "decision_id": item.decision_id,
                "transaction_id": item.transaction_id,
                "rule_id": item.rule_id,
                "category_id": item.category_id,
                "category": category.category_name if category else None,
                "matched_field": item.matched_field,
                "matched_value": item.matched_value,
                "decision_method": item.decision_method,
                "created_at": item.created_at.isoformat()
            })

        return jsonify({
            "status": "success",
            "total_decisions": len(result),
            "history": result
        })

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


# =====================================
# RECURRING PAYMENT APIs
# =====================================

@app.route("/api/recurring", methods=["GET"])
def get_recurring_payments():
    session = SessionLocal()

    try:
        series_list = session.query(RecurringSeries).filter_by(
            user_id=DEMO_USER_ID
        ).order_by(RecurringSeries.next_payment_date.asc()).all()

        result = []
        today = date.today()

        for series in series_list:
            occurrences = sorted(
                series.occurrences,
                key=lambda item: item.occurrence_date,
                reverse=True
            )

            payment_schedule = calculate_payment_status(
                series.next_payment_date,
                series.frequency,
                today
            )

            result.append({
                "series_id": series.series_id,
                "series_name": series.series_name,
                "account_id": series.account_id,
                "merchant_id": series.merchant_id,
                "merchant_name": (
                    series.merchant.merchant_name if series.merchant else None
                ),
                "category_id": series.category_id,
                "category": (
                    series.category.category_name if series.category else None
                ),
                "expected_amount": float(series.expected_amount),
                "frequency": series.frequency,
                "last_payment_date": (
                    series.last_payment_date.isoformat()
                    if series.last_payment_date else None
                ),
                "due_date": payment_schedule["due_date"],
                "next_payment_date": payment_schedule["next_payment_date"],
                "payment_status": payment_schedule["payment_status"],
                "days_overdue": payment_schedule["days_overdue"],
                "occurrence_count": series.occurrence_count,
                "status": series.status,
                "history": [
                    {
                        "occurrence_id": item.occurrence_id,
                        "transaction_id": item.transaction_id,
                        "occurrence_date": item.occurrence_date.isoformat(),
                        "actual_amount": float(item.actual_amount),
                        "status": item.status
                    }
                    for item in occurrences
                ]
            })

        return jsonify({
            "status": "success",
            "total_recurring": len(result),
            "recurring_payments": result
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()

# Automatically detect recurring transactions

# Automatically detect recurring transactions
@app.route("/api/recurring/detect", methods=["POST"])
def detect_recurring_payments():
    session = SessionLocal()

    try:
        transactions = session.query(Transaction).filter(
            Transaction.user_id == DEMO_USER_ID,
            Transaction.transaction_type.in_(["Expense", "Income"]),
            Transaction.status == "Completed"
        ).order_by(Transaction.transaction_date.asc()).all()

        groups = defaultdict(list)

        for transaction in transactions:
            description_key = normalize_description(
                transaction.description
            )

            if not description_key:
                continue

            merchant_key = (
                f"merchant:{transaction.merchant_id}"
                if transaction.merchant_id
                else f"description:{description_key}"
            )

            group_key = (
                transaction.account_id,
                transaction.transaction_type,
                merchant_key,
                description_key,
                abs(Decimal(str(transaction.amount))).quantize(Decimal("1"))
            )

            groups[group_key].append(transaction)

        detected_count = 0
        created_series = []

        for group_key, group_transactions in groups.items():

            if len(group_transactions) < 3:
                continue

            group_transactions.sort(
                key=lambda item: item.transaction_date
            )

            dates = [
                item.transaction_date
                for item in group_transactions
            ]

            frequency = identify_frequency(dates)

            if not frequency:
                continue

            # Validate payment intervals.
            gaps = [
                (dates[index] - dates[index - 1]).days
                for index in range(1, len(dates))
            ]

            if len(gaps) > 1:
                average_gap = statistics.mean(gaps)

                if any(
                    abs(gap - average_gap) >
                    max(7, average_gap * 0.25)
                    for gap in gaps
                ):
                    continue

            # Validate payment amounts.
            amounts = [
                abs(Decimal(str(item.amount)))
                for item in group_transactions
            ]

            average_amount = (
                sum(amounts) / Decimal(len(amounts))
            )

            if average_amount <= 0:
                continue

            account_id = group_key[0]
            first_transaction = group_transactions[0]
            last_transaction = group_transactions[-1]

            # Find an existing recurring series.
            existing_series = session.query(
                RecurringSeries
            ).filter_by(
                user_id=DEMO_USER_ID,
                account_id=account_id,
                series_name=(
                    first_transaction.description
                    or "Recurring Payment"
                )
            ).first()

            if existing_series:
                series = existing_series

            else:
                series_id = (
                    f"REC-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                )

                series = RecurringSeries(
                    series_id=series_id,
                    user_id=DEMO_USER_ID,
                    account_id=account_id,
                    merchant_id=first_transaction.merchant_id,
                    category_id=first_transaction.category_id,
                    series_name=(
                        first_transaction.description
                        or "Recurring Payment"
                    ),
                    expected_amount=average_amount.quantize(
                        Decimal("0.01")
                    ),
                    frequency=frequency,
                    last_payment_date=last_transaction.transaction_date,
                    next_payment_date=calculate_next_payment(
                        last_transaction.transaction_date,
                        frequency
                    ),
                    occurrence_count=0,
                    status="Active"
                )

                session.add(series)
                session.flush()

            # Get transactions already linked to this series.
            existing_transaction_ids = {
                item[0]
                for item in session.query(
                    RecurringOccurrence.transaction_id
                ).filter_by(
                    series_id=series.series_id
                ).all()
            }

            # Add only missing occurrences.
            for transaction in group_transactions:

                if transaction.transaction_id in existing_transaction_ids:
                    continue

                occurrence = RecurringOccurrence(
                    occurrence_id=f"OCC-{transaction.transaction_id}",
                    series_id=series.series_id,
                    transaction_id=transaction.transaction_id,
                    occurrence_date=transaction.transaction_date,
                    actual_amount=transaction.amount,
                    status=(
                        "Matched"
                        if abs(
                            Decimal(str(transaction.amount))
                            - average_amount
                        ) <= average_amount * Decimal("0.10")
                        else "Amount Mismatch"
                    )
                )

                session.add(occurrence)

            session.flush()

            # Update recurring series dates and amount.
            latest_date = max(
                group_transactions[-1].transaction_date,
                series.last_payment_date
                if series.last_payment_date
                else group_transactions[-1].transaction_date
            )

            series.last_payment_date = latest_date

            # Store the original scheduled due date.
            series.next_payment_date = calculate_next_payment(
                latest_date,
                frequency
            )

            series.frequency = frequency

            series.expected_amount = average_amount.quantize(
                Decimal("0.01")
            )

            # Recalculate occurrence count.
            series.occurrence_count = session.query(
                RecurringOccurrence
            ).filter_by(
                series_id=series.series_id
            ).count()

            # Calculate current payment status without
            # modifying the stored original due date.
            payment_schedule = calculate_payment_status(
                series.next_payment_date,
                series.frequency,
                date.today()
            )

            # Persist missed-payment review status and audit real changes.
            old_status = series.status

            if payment_schedule["payment_status"] == "Overdue":
                series.status = "Needs Review"

            if series.status != old_status:
                session.add(LifecycleEvent(
                    event_id=f"EVT-{uuid.uuid4().hex[:16]}",
                    entity_type="RecurringSeries",
                    entity_id=series.series_id,
                    event_type="Status Changed",
                    old_value=old_status,
                    new_value=series.status,
                    actor="system",
                    reason="Payment overdue"
                ))

            detected_count += 1

            created_series.append({
                "series_id": series.series_id,
                "series_name": series.series_name,
                "frequency": series.frequency,
                "expected_amount": float(series.expected_amount),
                "due_date": payment_schedule["due_date"],
                "next_payment_date": payment_schedule["next_payment_date"],
                "payment_status": payment_schedule["payment_status"],
                "days_overdue": payment_schedule["days_overdue"],
                "occurrence_count": series.occurrence_count
            })

        session.commit()

        return jsonify({
            "status": "success",
            "message": "Recurring payment detection completed",
            "detected_count": detected_count,
            "recurring_payments": created_series
        })

    except Exception as error:
        session.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()

# =====================================
# INSIGHT GENERATION HELPERS
# =====================================

def create_insight_id(unique_key):
    """Create a deterministic ID to prevent duplicate insights."""
    digest = hashlib.sha256(unique_key.encode("utf-8")).hexdigest()[:20]
    return f"INS-{digest}"



def save_or_update_insight(session, unique_key, user_id, insight_type,
                           severity, title, description,
                           metric_value=None, threshold_value=None,
                           category_id=None, budget_id=None,
                           transaction_id=None, series_id=None,
                           period_start=None, period_end=None):

    insight_id = create_insight_id(unique_key)

    insight = session.get(Insight, insight_id)

    if insight:
        # Do not reactivate an already resolved insight.
        if insight.status == "Resolved":
            return insight

        # Update existing active insight.
        old_insight_value = (
            f"status={insight.status}; severity={insight.severity}; "
            f"title={insight.title}; metric={insight.metric_value}"
        )
        insight.severity = severity
        insight.title = title
        insight.description = description
        insight.metric_value = metric_value
        insight.threshold_value = threshold_value
        insight.category_id = category_id
        insight.budget_id = budget_id
        insight.transaction_id = transaction_id
        insight.series_id = series_id
        insight.period_start = period_start
        insight.period_end = period_end
        insight.updated_at = datetime.utcnow()

        new_insight_value = (
            f"status={insight.status}; severity={insight.severity}; "
            f"title={insight.title}; metric={insight.metric_value}"
        )
        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Insight",
            entity_id=insight.insight_id,
            event_type="Updated",
            old_value=old_insight_value,
            new_value=new_insight_value,
            actor="system",
            reason="Insight refreshed by generation"
        ))

    else:
        insight = Insight(
            insight_id=insight_id,
            user_id=user_id,
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            metric_value=metric_value,
            threshold_value=threshold_value,
            category_id=category_id,
            budget_id=budget_id,
            transaction_id=transaction_id,
            series_id=series_id,
            period_start=period_start,
            period_end=period_end,
            status="New"
        )
        session.add(insight)
        session.add(LifecycleEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:16]}",
            entity_type="Insight",
            entity_id=insight.insight_id,
            event_type="Created",
            old_value=None,
            new_value=(
                f"status=New; type={insight.insight_type}; "
                f"severity={insight.severity}; title={insight.title}"
            ),
            actor="system",
            reason="Insight generated"
        ))

    return insight

# =====================================
# GENERATE INSIGHTS API
# =====================================


@app.route("/api/lifecycle-events", methods=["GET"])
def get_lifecycle_events():
    session = SessionLocal()

    try:
        entity_type = request.args.get("entity_type")
        entity_id = request.args.get("entity_id")

        try:
            limit = int(request.args.get("limit", 50))
        except ValueError:
            return jsonify({"status": "error", "message": "Limit must be an integer"}), 400

        if limit < 1 or limit > 100:
            return jsonify({"status": "error", "message": "Limit must be between 1 and 100"}), 400

        query = session.query(LifecycleEvent)

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        if entity_id:
            query = query.filter_by(entity_id=entity_id)

        events = query.order_by(
            LifecycleEvent.event_timestamp.desc(),
            LifecycleEvent.event_id.desc()
        ).limit(limit).all()

        return jsonify({
            "status": "success",
            "count": len(events),
            "events": [{
                "event_id": event.event_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "event_type": event.event_type,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "actor": event.actor,
                "reason": event.reason,
                "event_timestamp": event.event_timestamp.isoformat()
            } for event in events]
        })

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500

    finally:
        session.close()


@app.route("/api/insights/generate", methods=["POST"])
def generate_insights():
    session = SessionLocal()

    try:
        today = date.today()
        generated_count = 0

        # ---------------------------------
        # 1. BUDGET WARNING / OVERSPENDING
        # ---------------------------------

        active_budgets = session.query(Budget).filter(
            Budget.user_id == DEMO_USER_ID,
            Budget.status == "Active",
            Budget.period_start <= today,
            Budget.period_end >= today
        ).all()

        for budget in active_budgets:
            transactions = session.query(Transaction).filter(
                Transaction.user_id == DEMO_USER_ID,
                Transaction.category_id == budget.category_id,
                Transaction.status == "Completed",
                Transaction.transaction_date >= budget.period_start,
                Transaction.transaction_date <= today
            ).all()

            spent = sum(
                Decimal(str(item.amount))
                if item.transaction_type == "Expense"
                else -Decimal(str(item.amount))
                if item.transaction_type == "Refund"
                else Decimal("0")
                for item in transactions
            )

            spent = max(spent, Decimal("0"))
            budget_amount = Decimal(str(budget.budget_amount))
            percentage = (spent / budget_amount) * Decimal("100")

            category = session.get(Category, budget.category_id)
            category_name = category.category_name if category else "Unknown"

            if spent > budget_amount:
                save_or_update_insight(
                    session,
                    f"budget-overspending-{budget.budget_id}",
                    DEMO_USER_ID,
                    "Budget Overspending",
                    "High",
                    f"{category_name} budget exceeded",
                    f"You spent â‚¹{spent:.2f} against a budget of "
                    f"â‚¹{budget_amount:.2f}. Overspending: "
                    f"â‚¹{spent - budget_amount:.2f}.",
                    spent,
                    budget_amount,
                    category_id=budget.category_id,
                    budget_id=budget.budget_id,
                    period_start=budget.period_start,
                    period_end=budget.period_end
                )
                generated_count += 1

            elif percentage >= Decimal("80"):
                save_or_update_insight(
                    session,
                    f"budget-warning-{budget.budget_id}",
                    DEMO_USER_ID,
                    "Budget Warning",
                    "Medium",
                    f"{category_name} budget warning",
                    f"You have used {percentage:.1f}% of your "
                    f"â‚¹{budget_amount:.2f} budget.",
                    spent,
                    budget_amount,
                    category_id=budget.category_id,
                    budget_id=budget.budget_id,
                    period_start=budget.period_start,
                    period_end=budget.period_end
                )
                generated_count += 1

        # ---------------------------------
        # 2. MONTHLY SPENDING INCREASE
        # ---------------------------------

        current_start = today.replace(day=1)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end.replace(day=1)

        categories = session.query(Category).filter_by(
            category_type="Expense"
        ).all()

        for category in categories:
            current_transactions = session.query(Transaction).filter(
                Transaction.user_id == DEMO_USER_ID,
                Transaction.category_id == category.category_id,
                Transaction.status == "Completed",
                Transaction.transaction_type.in_(["Expense", "Income"]),
                Transaction.transaction_date >= current_start,
                Transaction.transaction_date <= today
            ).all()

            previous_transactions = session.query(Transaction).filter(
                Transaction.user_id == DEMO_USER_ID,
                Transaction.category_id == category.category_id,
                Transaction.status == "Completed",
                Transaction.transaction_type.in_(["Expense", "Income"]),
                Transaction.transaction_date >= previous_start,
                Transaction.transaction_date <= previous_end
            ).all()

            current_spending = sum(
                (Decimal(str(item.amount)) for item in current_transactions),
                Decimal("0")
            )

            previous_spending = sum(
                (Decimal(str(item.amount)) for item in previous_transactions),
                Decimal("0")
            )

            if (
                previous_spending > 0
                and current_spending > previous_spending * Decimal("1.20")
            ):
                increase = (
                    (current_spending - previous_spending)
                    / previous_spending
                ) * Decimal("100")

                save_or_update_insight(
                    session,
                    f"spending-increase-{category.category_id}-{current_start}",
                    DEMO_USER_ID,
                    "Spending Increase",
                    "Medium",
                    f"{category.category_name} spending increased",
                    f"Spending increased by {increase:.1f}% compared "
                    f"with the previous month.",
                    current_spending,
                    previous_spending,
                    category_id=category.category_id,
                    period_start=current_start,
                    period_end=today
                )
                generated_count += 1

        # ---------------------------------
        # 3. RECURRING PAYMENT ALERTS
        # ---------------------------------

        recurring_series = session.query(RecurringSeries).filter_by(
            user_id=DEMO_USER_ID,
            status="Active"
        ).all()

        for series in recurring_series:
            payment_info = calculate_payment_status(
                series.next_payment_date,
                series.frequency,
                today
            )

            if payment_info["payment_status"] == "Overdue":
                save_or_update_insight(
                    session,
                    f"recurring-overdue-{series.series_id}-{payment_info['due_date']}",
                    DEMO_USER_ID,
                    "Recurring Payment",
                    "High",
                    f"{series.series_name} payment is overdue",
                    f"Expected payment of â‚¹{series.expected_amount} "
                    f"was due on {payment_info['due_date']}. "
                    f"It is {payment_info['days_overdue']} days overdue.",
                    Decimal(str(series.expected_amount)),
                    None,
                    category_id=series.category_id,
                    series_id=series.series_id
                )
                generated_count += 1

            elif (
                payment_info["payment_status"] == "Upcoming"
                and (series.next_payment_date - today).days <= 7
            ):
                save_or_update_insight(
                    session,
                    f"recurring-upcoming-{series.series_id}-{payment_info['due_date']}",
                    DEMO_USER_ID,
                    "Recurring Payment",
                    "Low",
                    f"{series.series_name} payment is coming up",
                    f"Expected payment of â‚¹{series.expected_amount} "
                    f"is due on {payment_info['due_date']}.",
                    Decimal(str(series.expected_amount)),
                    None,
                    category_id=series.category_id,
                    series_id=series.series_id
                )
                generated_count += 1

        # ---------------------------------
        # 4. UNCATEGORIZED TRANSACTIONS
        # ---------------------------------

        # First, resolve old alerts for transactions
        # that now have a category assigned.
        existing_uncategorized_insights = session.query(Insight).filter(
            Insight.user_id == DEMO_USER_ID,
            Insight.insight_type == "Uncategorized Transaction",
            Insight.transaction_id.isnot(None)
        ).all()

        for old_insight in existing_uncategorized_insights:
            linked_transaction = session.get(
                Transaction,
                old_insight.transaction_id
            )

            if (
                not linked_transaction
                or linked_transaction.category_id is not None
                or linked_transaction.status != "Completed"
            ):
                if old_insight.status != "Resolved":
                    previous_status = old_insight.status
                    old_insight.status = "Resolved"
                    old_insight.updated_at = datetime.utcnow()

                    session.add(LifecycleEvent(
                        event_id=f"EVT-{uuid.uuid4().hex[:16]}",
                        entity_type="Insight",
                        entity_id=old_insight.insight_id,
                        event_type="Status Changed",
                        old_value=previous_status,
                        new_value="Resolved",
                        actor="system",
                        reason=(
                            "Uncategorized transaction was categorized, "
                            "deleted or is no longer completed"
                        )
                    ))

        # Then create/update alerts only for transactions
        # that are still uncategorized.
        uncategorized = session.query(Transaction).filter(
            Transaction.user_id == DEMO_USER_ID,
            Transaction.status == "Completed",
            Transaction.category_id.is_(None)
        ).all()

        for transaction in uncategorized:
            save_or_update_insight(
                session,
                f"uncategorized-{transaction.transaction_id}",
                DEMO_USER_ID,
                "Uncategorized Transaction",
                "Medium",
                "Transaction needs categorization",
                f"Transaction '{transaction.description}' "
                f"for â‚¹{transaction.amount} has no category assigned.",
                Decimal(str(transaction.amount)),
                None,
                transaction_id=transaction.transaction_id
            )
            generated_count += 1

        session.commit()

        total_insights = session.query(Insight).filter_by(
            user_id=DEMO_USER_ID
        ).count()

        return jsonify({
            "status": "success",
            "message": "Insight generation completed successfully",
            "generated_or_updated_count": generated_count,
            "total_saved_insights": total_insights
        })

    except Exception as error:
        session.rollback()
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()

# =====================================
# GET INSIGHTS API
# =====================================

@app.route("/api/insights", methods=["GET"])
def get_insights():
    session = SessionLocal()

    try:
        insights = session.query(Insight).filter_by(
            user_id=DEMO_USER_ID
        ).order_by(Insight.created_at.desc()).all()

        result = []

        for item in insights:
            category = (
                session.get(Category, item.category_id)
                if item.category_id else None
            )

            result.append({
                "insight_id": item.insight_id,
                "insight_type": item.insight_type,
                "severity": item.severity,
                "title": item.title,
                "description": item.description,
                "metric_value": (
                    float(item.metric_value)
                    if item.metric_value is not None else None
                ),
                "threshold_value": (
                    float(item.threshold_value)
                    if item.threshold_value is not None else None
                ),
                "category_id": item.category_id,
                "category": category.category_name if category else None,
                "budget_id": item.budget_id,
                "transaction_id": item.transaction_id,
                "series_id": item.series_id,
                "period_start": (
                    item.period_start.isoformat()
                    if item.period_start else None
                ),
                "period_end": (
                    item.period_end.isoformat()
                    if item.period_end else None
                ),
                "status": item.status,
                "created_at": item.created_at.isoformat()
            })

        return jsonify({
            "status": "success",
            "total_insights": len(result),
            "insights": result
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()


# =====================================
# UPDATE INSIGHT STATUS API
# =====================================

@app.route("/api/insights/<insight_id>", methods=["PUT"])
def update_insight(insight_id):
    session = SessionLocal()

    try:
        data = request.get_json(silent=True) or {}

        insight = session.get(Insight, insight_id)

        if not insight or insight.user_id != DEMO_USER_ID:
            return jsonify({
                "status": "error",
                "message": "Insight not found"
            }), 404

        allowed_statuses = ["New", "Acknowledged", "Resolved"]
        new_status = data.get("status")

        if new_status not in allowed_statuses:
            return jsonify({
                "status": "error",
                "message": "Status must be New, Acknowledged or Resolved"
            }), 400

        old_status = insight.status
        insight.status = new_status
        insight.updated_at = datetime.utcnow()

        if old_status != new_status:
            session.add(LifecycleEvent(
                event_id=f"EVT-{uuid.uuid4().hex[:16]}",
                entity_type="Insight",
                entity_id=insight.insight_id,
                event_type="Status Changed",
                old_value=old_status,
                new_value=new_status,
                actor="system",
                reason="Insight status changed through API"
            ))

        session.commit()

        return jsonify({
            "status": "success",
            "message": "Insight status updated successfully",
            "insight_id": insight.insight_id,
            "new_status": insight.status
        })

    except Exception as error:
        session.rollback()
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        session.close()

# =====================================
# START APPLICATION
# =====================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)

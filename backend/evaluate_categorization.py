import csv
import json
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "reproducibility_tests" / "full_run2"
DB = ROOT / "pennywise_dataset.db"
OUT = ROOT / "dataset_exports"
OUT.mkdir(exist_ok=True)

def read_csv(name):
    with (BASE / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

transactions = read_csv("transactions")
truth_rows = read_csv("ground_truth")
truth = {r["transaction_id"]: r for r in truth_rows}

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rules = conn.execute("""
    SELECT rule_id, category_id, match_field, match_type,
           match_value, priority, is_active,
           effective_from, effective_to, created_at
    FROM category_rules
    WHERE is_active = 1
    ORDER BY priority ASC, created_at ASC
""").fetchall()

description_rules = [r for r in rules if r["match_field"] == "description"]
merchant_rules = [r for r in rules if r["match_field"] == "merchant"]

def predict(description, tx_date):
    source = (description or "").strip().lower()

    for rule in description_rules:
        if tx_date < rule["effective_from"]:
            continue
        if rule["effective_to"] and tx_date > rule["effective_to"]:
            continue

        value = rule["match_value"].strip().lower()

        if rule["match_type"] == "contains":
            matched = value in source
        elif rule["match_type"] == "exact":
            matched = source == value
        elif rule["match_type"] == "starts_with":
            matched = source.startswith(value)
        else:
            matched = False

        if matched:
            return rule["category_id"], rule["rule_id"]

    return "", ""

results = []
confusion = defaultdict(Counter)
tp = Counter()
fp = Counter()
fn = Counter()

correct = 0
matched = 0
intentional_uncategorized = 0
evaluated = 0

for row in transactions:
    label = truth[row["transaction_id"]]

    if label["is_intentionally_uncategorized"] == "1":
        intentional_uncategorized += 1
        continue

    expected = label["expected_category_id"]
    predicted, rule_id = predict(
        row["description"], row["transaction_date"]
    )

    evaluated += 1

    if predicted:
        matched += 1

    if predicted == expected and predicted:
        correct += 1
        tp[expected] += 1
    else:
        fn[expected] += 1
        if predicted:
            fp[predicted] += 1

    confusion[expected][predicted or "UNCATEGORIZED"] += 1

    results.append({
        "transaction_id": row["transaction_id"],
        "expected_category_id": expected,
        "predicted_category_id": predicted,
        "matched_rule_id": rule_id,
        "correct": int(predicted == expected and bool(predicted))
    })

classes = sorted(set(
    r["expected_category_id"] for r in results
) | set(r["predicted_category_id"] for r in results if r["predicted_category_id"]))

metrics = {}

for category in classes:
    precision = tp[category] / (tp[category] + fp[category]) if tp[category] + fp[category] else 0
    recall = tp[category] / (tp[category] + fn[category]) if tp[category] + fn[category] else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0

    metrics[category] = {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "support": tp[category] + fn[category]
    }

macro_precision = sum(x["precision"] for x in metrics.values()) / len(metrics) if metrics else 0
macro_recall = sum(x["recall"] for x in metrics.values()) / len(metrics) if metrics else 0
macro_f1 = sum(x["f1_score"] for x in metrics.values()) / len(metrics) if metrics else 0

report = {
    "dataset": "full_run2",
    "evaluation_method": "SQLite description-based CategoryRule simulation",
    "transactions": len(transactions),
    "ground_truth": len(truth_rows),
    "evaluated_transactions": evaluated,
    "intentionally_uncategorized_excluded": intentional_uncategorized,
    "matched_transactions": matched,
    "missed_classifications": evaluated - matched,
    "accuracy": round(correct / evaluated, 4) if evaluated else 0,
    "rule_coverage": round(matched / evaluated, 4) if evaluated else 0,
    "uncategorized_rate": round((evaluated - matched) / evaluated, 4) if evaluated else 0,
    "macro_precision": round(macro_precision, 4),
    "macro_recall": round(macro_recall, 4),
    "macro_f1": round(macro_f1, 4),
    "description_rules_available": len(description_rules),
    "merchant_rules_not_evaluated": len(merchant_rules),
    "per_category": metrics,
    "confusion_matrix": {
        category: dict(values)
        for category, values in confusion.items()
    }
}

json_path = OUT / "categorization_evaluation_report.json"
json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

csv_path = OUT / "categorization_predictions.csv"
with csv_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

conn.close()

print("\nCATEGORIZATION EVALUATION")
print("-" * 40)
for key in [
    "transactions", "evaluated_transactions",
    "intentionally_uncategorized_excluded",
    "matched_transactions", "missed_classifications",
    "accuracy", "rule_coverage", "uncategorized_rate",
    "macro_precision", "macro_recall", "macro_f1"
]:
    print(f"{key}: {report[key]}")

print("\nPER CATEGORY:")
for category, values in metrics.items():
    print(category, values)

print("\nREPORT:", json_path)
print("PREDICTIONS:", csv_path)
print("EVALUATION: COMPLETED")

# PennyWise Edge Case Test Report

- Overall status: **PASSED**
- Passed: 5/5

| Scenario | Test | Result | Details |
|---|---|---|---|
| EDGE-001 | Transfer double counting | PASSED | {'transfer_group_id': 'TRF-DSU-000001-0001', 'pair_count': 2, 'expense_total': 0, 'transfer_count': 2} |
| EDGE-002 | Refund linked to original expense | PASSED | {'refund_id': 'DS-TXN-000000038', 'refund_amount': 5723.62, 'original_transaction_id': 'DS-TXN-000000101', 'original_type': 'Expense', 'original_amount': 7072.45, 'refund_user': 'DSU-000001', 'original_user': 'DSU-000001', 'refund_merchant': 'MER-019', 'original_merchant': 'MER-019', 'refund_date': '2026-01-10', 'original_date': '2025-12-24', 'total_refunds': 5723.62} |
| EDGE-003 | Missing recurring payment detected | PASSED | {'series_id': 'DS-REC-DSU-000001-MER-001', 'series_name': 'Netflix Subscription', 'next_payment_date': '2026-05-01', 'matching_occurrences': 0} |
| EDGE-004 | Timezone boundary conversion | PASSED | UTC=2025-12-31T18:45:00+00:00, Local=2026-01-01T00:15:00+05:30 |
| EDGE-005 | Invalid budget category rejected | PASSED | FOREIGN KEY constraint failed |

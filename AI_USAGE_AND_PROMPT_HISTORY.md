# PennyWise — AI Usage Disclosure and Prompt History

## Project
PennyWise: transaction categorization, recurring payment detection, budget comparison, and synthetic financial data generation for the YottaFlex 72-hour code challenge.

## AI assistance disclosure
ChatGPT was used extensively as an interactive coding and review assistant. Assistance included interpreting the problem statement, proposing implementation approaches, drafting and revising Python/Flask/SQLAlchemy and React-related code, suggesting SQL queries and PowerShell commands, debugging errors, designing synthetic dataset generation and validation checks, writing documentation, and interpreting test outputs.

AI assistance was particularly significant in:
- Designing deterministic, fixed-seed synthetic data generation with related users, accounts, merchants, transactions, budgets, recurring series, and labelled outcomes.
- Developing validation and reconciliation procedures for foreign keys, duplicate IDs, transfers, refunds, recurring records, and derived amounts.
- Building and debugging backend categorization, recurring-payment detection, budget, and insight workflows.
- Preparing evaluation scripts, reproducibility checks, documentation, and submission-readiness reviews.

AI-generated suggestions were not accepted as proof of correctness on their own. The project was exercised through local commands, and outputs were reviewed in conversation. This disclosure does not claim that every line was independently authored or audited without AI.

## Work reviewed and validated by the candidate
Based on the available development conversation, the candidate executed commands in a local Windows environment, supplied error logs and test outputs, checked backend endpoints, ran generator/validation/evaluation scripts, inspected generated reports, built the frontend, and pushed code to GitHub. Reported checks include:

| Verification | Reported outcome |
| --- | --- |
| Full synthetic generation | 1,000 users and 500,000 transactions across 12 months |
| Full dataset validation | PASS |
| Ledger reconciliation | PASS |
| Deterministic reproducibility | Matching checksums across two complete runs |
| Five labelled edge-case fixtures | PASS |
| Categorization evaluation | Accuracy 57.05%; macro F1 63.69% |
| Offline recurring labelled evaluation | Precision 1.0; recall approximately 0.999667 |
| Isolated Flask recurring API test | One labelled positive detected; negative excluded |
| Backend GET API smoke tests | 8/8 PASS |
| Frontend production build | PASS |

These are **reported local test results**, not independently rerun in this document. Evaluation metrics are not a guarantee of production accuracy.

## Design decisions and limitations
- Generated data is synthetic and uses a fixed seed to enable reproducibility.
- Ground-truth labels are kept separate from input features.
- Deliberate anomaly cases are labelled and tested separately rather than corrupting the valid baseline.
- The live Flask recurring detector is scoped to the demo user; the full-dataset recurring evaluation uses an offline equivalent, not a 500,000-transaction Flask API run.
- The frontend production build and backend API tests passed separately; a complete browser-based end-to-end test was not confirmed in the available record.
- Synthetic-label evaluation should not be interpreted as independent real-world model performance.

## Prompt history — required companion material
**Important:** This document is an AI-use summary, **not a substitute for the original prompt history**. To satisfy the requirement to submit prompt history, add the authentic conversation export or transcripts to the repository, for example:

```
submission/ai_prompt_history/
  README.md
  conversation_01.txt
  conversation_02.txt
  ...
```

Include the candidate's original prompts and assistant responses in chronological order where available. Do not reconstruct missing prompts or present a summary as a verbatim transcript. Review exports for passwords, access tokens, private financial data, personal identifiers, and unrelated private conversation content before making the repository public. If only partial history is available, identify it honestly as partial.

### Representative prompt themes (summary, not verbatim transcript)
1. Interpret the YottaFlex transaction categorization, recurring payments, and budgeting challenge.
2. Build and debug Flask backend and SQLAlchemy entities, constraints, and API endpoints.
3. Implement recurring detection and test positive/negative transaction sequences.
4. Generate deterministic 1,000-user / 500,000-transaction synthetic data with fixed seed.
5. Validate refunds, transfers, IDs, foreign keys, recurring labels, and ledger totals.
6. Produce ground-truth exports, data dictionary, schema, lifecycle documentation, and reproducibility evidence.
7. Verify GitHub submission readiness and disclose AI usage transparently.

## Repository and execution
Repository: https://github.com/Bhargavi9391/PennyWise

See the repository's main `README.md` for installation, execution, and test commands. The candidate should review this disclosure for accuracy and commit it alongside authentic prompt-history material before final submission.

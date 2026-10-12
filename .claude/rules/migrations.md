---
paths:
  - "backend/migrations/**"
  - "backend/app/**/models.py"
---

# Database migrations

- Never edit a migration that may have been applied anywhere shared; write a new one.
- Every schema change updates `docs/DATABASE_SCHEMA.md` (and `docs/DATA_DICTIONARY.md` if meanings change) in the same commit.
- Append-only tables (`text_revisions`, `review_events`, `audit_events`, `consent_records`, `renditions`, `dataset_release_items`, `processing_runs`) must keep their UPDATE/DELETE-blocking triggers. Use `lkd_reject_change()` for fully immutable rows, `lkd_guard_columns(...)` when listed columns may change, `lkd_freeze_columns(...)` to pin identity columns (ADR-020); update the column list when you change a guarded table.
- Destructive changes use expand → migrate → contract.
- Follow the `database-design` skill for the full procedure.

---
paths:
  - "backend/migrations/**"
  - "backend/app/**/models.py"
---

# Database migrations

- Never edit a migration that may have been applied anywhere shared; write a new one.
- Every schema change updates `docs/DATABASE_SCHEMA.md` (and `docs/DATA_DICTIONARY.md` if meanings change) in the same commit.
- Append-only tables (`text_revisions`, `review_events`, `audit_events`, `consent_records`, `renditions`, `dataset_release_items`, `processing_runs`) must keep their UPDATE/DELETE-blocking triggers.
- Destructive changes use expand → migrate → contract.
- Follow the `database-design` skill for the full procedure.

---
name: database-design
description: Procedure for changing Lokdhara's PostgreSQL schema — Alembic migrations, constraints, indexes, append-only and versioned tables, restricted fields, and the effective-access predicate. Use when adding or altering tables, columns, enums, indexes, triggers, DB roles, or SQLAlchemy models.
---

# Database design and migrations

Source of truth: `docs/DATABASE_SCHEMA.md`, `docs/DATA_DICTIONARY.md`, `docs/ACCESS_CONTROL.md`, ADR-005/011/012/016.

## Before writing a migration

1. Read the affected tables in `docs/DATABASE_SCHEMA.md` and decide for each new column: required? immutable? versioned? restricted? indexed/searchable? exported? Record the answers in the schema doc and data dictionary.
2. Collect only what a documented requirement needs (data minimisation). Any new personal or demographic field needs a consent basis and a `privacy-review`.
3. Check workflow coverage: does the change keep every flow in `docs/USER_FLOWS.md` working?

## Conventions

- PostgreSQL 18; `id uuid PRIMARY KEY DEFAULT uuidv7()`; `timestamptz` in UTC.
- Enumerations as `text` + `CHECK (col IN (...))`, not PostgreSQL ENUM types.
- Foreign keys always declared; choose `ON DELETE RESTRICT` by default. Deletion of personal data goes through the erasure routine, not cascades.
- Append-only tables (`text_revisions`, `review_events`, `audit_events`, `consent_records`, `renditions`, `dataset_release_items`, `processing_runs`, `prompts`) keep triggers that reject UPDATE/DELETE for role `app_rw`; only `app_erasure` may delete/tombstone.
- JSONB only for open-ended metadata, with an allow-list validated in the API.
- Restricted data (identity, contacts) lives in separate tables with application-level encryption.
- Visibility must go through the effective-access predicate; never add a query path that bypasses it.

## Migration procedure

1. `uv run alembic revision -m "<imperative description>"`; write explicit `upgrade()` and `downgrade()`; do not rely blindly on autogenerate.
2. Never edit a migration that may have run on a shared database; add a new one.
3. Destructive changes: expand (add new) → migrate data → contract (drop old) in a later release.
4. Run locally: upgrade → downgrade -1 → upgrade; run the integration test suite against real PostgreSQL.
5. Update `docs/DATABASE_SCHEMA.md` (and data dictionary / API spec if affected) in the same commit.
6. If the change alters an architectural decision, add an ADR.

## Tests

- Constraint and trigger tests (append-only enforcement, CHECKs, FK behaviour).
- Effective-access tests: Python rule and SQL predicate must agree on the shared case table.
- Migration round-trip test in CI.

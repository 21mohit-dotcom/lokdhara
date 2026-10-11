# Observability and Backups

Status: **Proposed.**

## 1. Logging

- Structured JSON logs to stdout from API and worker; Docker log rotation on the host (e.g., 7 × 50 MB).
- Every request has a `request_id` (propagated to jobs as `correlation_id`).
- **Never logged:** audio, text content, speaker names/contacts, emails/phones, passwords, tokens, cookies, raw IP addresses, object keys of consent evidence.
- A logging filter redacts known sensitive keys; a unit test feeds sample payloads through the logger and asserts redaction.

## 2. Metrics and health (lightweight)

| Signal | Source | Alert when |
|--------|--------|-----------|
| `/healthz`, `/readyz` | API | External uptime monitor fails 3 checks |
| Queue depth and oldest queued job age | DB query exposed on admin dashboard | Oldest job > 1 hour |
| Dead jobs count | DB | > 0 new in 24 h (daily digest) |
| Disk usage on VM | Host | > 80% |
| Backup success | Backup job writes status row | Missing for > 26 h |
| Error rate (5xx) | Logs / error tracker | Spike |
| Login failures | Audit events | Unusual spike |

MVP uses an admin dashboard page and a daily digest to maintainers (delivery channel to be chosen in M8, e.g. email); no Prometheus/Grafana stack until there is a need.

Optional error tracking (e.g., Sentry free tier): only with `send_default_pii` disabled, request bodies not captured, and a scrubbing hook; otherwise rely on logs.

## 3. Backups

| What | How | Frequency | Retention | Where |
|------|-----|-----------|-----------|-------|
| PostgreSQL | `pg_dump -Fc` → encrypt (`age`, public key on server, private key offline with two admins) → upload | Nightly + before each deploy | 30 daily, 12 monthly | Backup bucket, separate credentials (write-only key on server) |
| `originals/` | Bucket versioning + (if supported) object lock; optional cross-provider replica later | Continuous | Versions retained ≥ 30 days after deletion except erasure | Primary storage |
| `consent-evidence/` | Versioning; included in replica | Continuous | Per retention policy | Primary storage |
| `derived/` | Not backed up (re-creatable from originals) | — | — | — |
| Configuration | Infra files in Git; secrets in password manager | On change | — | — |

## 4. Restore drills

- Quarterly: restore latest DB dump into a scratch environment, run integrity checks (row counts, foreign keys, checksum sample of originals).
- After any restore to production: **re-apply all completed withdrawal requests** made after the backup timestamp before reopening the service (the `withdrawal_requests` export is also kept outside the DB backup for this purpose).
- Record each drill (date, duration, problems) in `docs/ops/restore-drills.md` (created when the first drill happens).

## 5. Targets (pilot)

- RPO (max data loss): 24 hours for metadata; near-zero for originals (versioned storage).
- RTO (time to restore): 48 hours.

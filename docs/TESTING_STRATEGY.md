# Testing Strategy

Status: **Proposed.** Tools are confirmed in Milestone 1.

## 1. Principles

1. **Test the rules that protect people first**: consent gating, effective access, withdrawal propagation, export allow-list. These get the most exhaustive tests.
2. **Pure functions for logic** (audio metric parsing, text validation, effective access) so they can be tested without a database.
3. **Real PostgreSQL in integration tests**, not SQLite — constraints, triggers, and JSONB behaviour must be the real ones.
4. **Synthetic data only.** Fixtures are generated (FFmpeg sine/silence/noise, programmatic text in all scripts). No real recordings in the repository, ever.
5. A bug fix starts with a failing test.

## 2. Test pyramid

| Level | Tooling | Scope | Runs |
|-------|---------|-------|------|
| Unit (backend) | pytest | Pure functions: validators, normalisation, script detection, metric parsers, permission rules, state machine | Every commit (CI) |
| Unit (frontend) | Vitest + Testing Library | Components, i18n completeness, draft storage logic | CI |
| Integration (backend) | pytest + httpx + PostgreSQL service container + local object store | API endpoints end-to-end through DB and storage; migrations | CI |
| Worker integration | pytest + FFmpeg in CI image | Real FFmpeg on generated fixtures: validate, analyse, renditions, dedupe | CI |
| End-to-end | Playwright (Chromium; WebKit for Safari approximation) | Contributor submits (fake media stream), reviewer approves, researcher sees item | CI on main + nightly |
| Manual device tests | Real low-end Android, iPhone if available | Recording, upload on throttled network, Nag Mundari rendering | Each milestone from M3 |

## 3. Required test suites by risk

### 3.1 Upload security

| Case | Expected |
|------|----------|
| File > size limit | `413`, nothing in quarantine after request |
| HTML/EXE/ZIP renamed to `.mp3`/`.wav` | `415 bad_signature` |
| Valid header + truncated body | Worker `corrupt_audio` |
| Polyglot / crafted container (e.g., WAV header + garbage) | `corrupt_audio` |
| HLS/concat playlist disguised as audio | Rejected; no network access attempted (protocol whitelist) |
| Path traversal in filename (`../../x.wav`) | Ignored; server-generated key |
| Duplicate request with same `Idempotency-Key` | One recording created |
| Upload by user without consent attached | `422 consent_required` |
| Upload to another user's submission | `403/404` |

### 3.2 Permissions (table-driven)

A single YAML/py table of `(role set, item state, flags, consent, ownership) → expected (view, actions)` derived from [ACCESS_CONTROL.md](ACCESS_CONTROL.md), executed against both the Python `can_view` function and the SQL predicate, and against the HTTP layer for a representative subset. The two implementations must agree on every row.

Must include: reviewer cannot review own submission; researcher cannot see unapproved or non-research-consented items; culturally restricted items only visible with scope; withdrawn items visible only to admins.

### 3.3 Data integrity

| Case | Expected |
|------|----------|
| UPDATE/DELETE on `text_revisions`, `review_events`, `audit_events`, `consent_records` (non-status) as `app_rw` | Fails (trigger) |
| Erasure routine as `app_erasure` | Succeeds and writes tombstones + audit |
| Translation without source layer; transcription without recording | DB CHECK failure |
| Two concurrent revisions with same base | One `201`, one `409` |
| Original object checksum after processing | Unchanged |
| Re-running a rendition job | Same output checksum (deterministic), original untouched |
| Freeze release including withdrawn/non-consented item | Blocked by D1/D2 |
| Export package fields | Exactly the allow-list (snapshot test) |
| Withdrawal after freeze | Item flagged in release; export of that release blocked; new PATCH preview excludes item |

### 3.4 Text processing

Property-based tests (Hypothesis) for: NFC idempotence, original preserved exactly, disallowed characters always rejected, ZWJ/ZWNJ preserved. Example-based tests in Devanagari, Latin with diacritics, and Nag Mundari (U+1E4D0–U+1E4FF).

### 3.5 Audio processing

Generated fixtures: 3 s sine (WAV/FLAC/MP3/Opus-WebM/AAC-M4A), 5 s silence, clipped square wave, 0.5 s clip, stereo with different channels, 8 kHz and 96 kHz edge cases. Assert probe values, flags, rendition formats, and that `processing_runs` records tool versions.

## 4. CI checks (GitHub Actions, proposed)

| Job | Blocks merge |
|-----|--------------|
| Backend: `ruff check`, `ruff format --check`, `mypy`, `pytest` (unit + integration with Postgres service) | Yes |
| Frontend: `eslint`, `tsc --noEmit`, `vitest`, production build + bundle-size report | Yes (size budget warning first, blocking from M3) |
| Migrations: upgrade from empty → head, downgrade one step, upgrade again | Yes |
| Forbidden files: fail on audio extensions, `data/`, `storage/`, `exports/`, `.env` (except `.env.example`), DB dumps | Yes |
| Secret scan (gitleaks or GitHub secret scanning) | Yes |
| Dependency audit (`pip-audit`, `npm audit --omit=dev`) | No (reported) |
| Playwright E2E | On main + nightly |

## 5. Coverage expectations

Coverage percentage is a signal, not a goal. Required: 100% branch coverage of `effective_access`, consent gating, export allow-list, and state machine transitions; meaningful coverage elsewhere.

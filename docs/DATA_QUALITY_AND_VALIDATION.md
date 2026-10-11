# Data Quality and Validation

Status: **Proposed.** Distinguishes *hard validation* (input is rejected), *quality signals* (advisory, shown to reviewers), and *dataset checks* (run before a release can be frozen).

## 1. Hard validation (reject)

| Area | Check | Where | Error code |
|------|-------|-------|-----------|
| Audio | Size ≤ limit | Proxy + API | `too_large` |
| Audio | Magic-byte signature in allow-list | API | `bad_signature` |
| Audio | Probe succeeds; exactly one audio stream; values in range | Worker | `unsupported_format`, `out_of_range` |
| Audio | Full decode without errors | Worker | `corrupt_audio` |
| Audio | Duration ≥ 1 s and ≤ 30 min | Worker | `too_short`, `too_long` |
| Text | UTF-8, length limits, disallowed characters | API | see [TEXT_PROCESSING_PIPELINE.md §2](TEXT_PROCESSING_PIPELINE.md#2-safety-validation-reject-do-not-alter) |
| Metadata | Enumerations, required fields, JSONB allow-list for `collection_context` | API (Pydantic) | `validation_error` with field path |
| Consent | Active consent with `allow_store_and_review` before leaving draft | API service | `consent_required` |
| Consent | Speaker flagged `minor` without guardian consent | API service | `guardian_consent_required` |
| Links | Transcription has a recording; translation has a source layer | DB CHECK + API | `invalid_link` |
| Concurrency | Revision `base_revision_id` must be current | API | `409 revision_conflict` |

## 2. Quality signals (advisory)

| Signal | Computed by | Shown to |
|--------|-------------|----------|
| `silent`, `very_quiet`, `clipping`, `too_short` | Audio analysis | Contributor (where detectable before upload), reviewer |
| `possible_duplicate` | Hash / text match | Reviewer |
| Declared vs. detected script mismatch | Text pipeline | Contributor (warning), reviewer |
| Uncertainty markup present | Text pipeline | Reviewer |
| Translation stale (source revised after translation) | Revision links | Reviewer, researcher |
| Lossy source | Audio probe | Researcher, export |
| VAD speech ratio (optional) | Silero VAD | Reviewer only, labelled "estimate" |

Signals never change status automatically in MVP. Thresholds are initial guesses and must be tuned against pilot data, with changes recorded here.

## 3. Review quality

- Reviewer cannot review own submission (enforced in service and tested).
- Every reject/request-changes requires a reason code.
- Sample audit: an admin re-reviews a random 5% of approved items monthly in the pilot; disagreements are logged as `dispute_revision` events and inform reviewer guidance.
- Inter-reviewer agreement measurement is future work (needs two-reviewer workflow).

## 4. Dataset pre-freeze checks (automated, must all pass)

| # | Check |
|---|-------|
| D1 | Every item `approved` and not `withdrawn`. |
| D2 | Every item's effective consent allows the release purpose (re-computed at freeze time, not cached). |
| D3 | No item has an excluding restriction flag for this purpose. |
| D4 | Every referenced file exists and its stored checksum matches a fresh hash. |
| D5 | Every transcription included as "verified" has `verification_status = verified` and no unresolved uncertainty. |
| D6 | No export field outside the allow-list (schema test on a generated sample). |
| D7 | Licence and data card present for external/public/AI-training purposes. |
| D8 | Summary statistics (counts by dialect label, script, content type, duration) generated and included in the data card. |
| D9 | No speaker contributes more than a configurable share of total duration without a note in the data card (bias awareness, not a block). |

## 5. Data integrity monitoring (scheduled jobs)

| Job | Frequency | Action on failure |
|-----|-----------|-------------------|
| Checksum audit of a random sample of originals | Weekly | Alert admin; restore from backup/versioned object. |
| Orphan check: objects with no DB row / rows with missing objects | Weekly | Report; never auto-delete originals. |
| Quarantine cleanup | Hourly | Delete quarantine objects older than 24 h with no promotion. |
| Consent consistency: submissions linked to withdrawn speakers still visible | Daily | Alert admin; hide immediately. |

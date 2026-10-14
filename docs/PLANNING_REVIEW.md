# Planning Review — Milestone 0

Date: 2026-10-11 · Branch: `docs/planning-foundation` · Status: **Approved by the project owner on 2026-10-11.**

> Note (2026-10-14): `CLAUDE.md` is now `AGENTS.md` and the `.claude/` folder is now `.agents/`. This review keeps the old names as they were on the review date.

## 1. Decisions proposed (all need approval)

| Area | Proposal | Doc |
|------|----------|-----|
| Scope | Invite-only Mundari language MVP; no heritage modules, ASR/MT, public browsing, or open sign-up | MVP_SCOPE |
| Shape | Modular monolith: FastAPI API + worker, one codebase | ADR-002 |
| Frontend | React + TypeScript + Vite SPA, Hindi/English UI, drafts on device | ADR-003 |
| Backend | Python 3.13 + FastAPI + SQLAlchemy 2 + Alembic | ADR-004 |
| Database | PostgreSQL 18; JSONB only for open-ended metadata | ADR-005 |
| Storage | S3-compatible behind an interface; local adapter in dev; provider chosen at M8 | ADR-006 |
| Jobs | PostgreSQL-backed queue (Procrastinate, to be confirmed by spike) | ADR-007 |
| Auth | Invite-only, server-side sessions, Argon2id, role + consent-based filtering | ADR-008 |
| Data integrity | Immutable originals; verbatim text; append-only revisions with provenance | ADR-009–011 |
| Consent | Versioned records, seven separate permissions, most-restrictive effective access | ADR-012 |
| Datasets | Frozen manifests + on-demand export packages; never in Git | ADR-013 |
| AI | No ASR/MT in MVP; machine output never ground truth | ADR-014 |
| Hosting | One VM + Docker Compose (institutional server preferred) | ADR-015 |
| Recording modes | Free, prompted (image/situation), and read speech, with a versioned prompt library | ADR-018, RECORDING_MODES |
| Pilot safety default | **No minors in the pilot** until guardian procedure is approved | CONSENT §3.4 |

## 2. Checks performed

| # | Check | Result |
|---|-------|--------|
| 1 | All documents listed in the brief exist | ✅ all 27 documents named in the brief exist in `docs/` (incl. this review), plus RECORDING_MODES.md |
| 2 | Architecture decisions match the selected stack | ✅ ADR-002–016 match TECH_STACK_EVALUATION §2, SYSTEM_ARCHITECTURE, CLAUDE.md |
| 3 | Database model supports documented workflows | ✅ Mapping table in DATABASE_SCHEMA §9 covers flows F1–F7. Two gaps found and fixed during review: translation staleness needed `source_revision_id`; reviewer scope needed `user_roles.scope`; consent widening needed `applies_to_past_contributions`. |
| 4 | Privacy and consent reflected in architecture | ✅ Separate identity table and evidence bucket; effective-access rule in one place; purpose-gated releases; export allow-list; withdrawal path across all lifecycle stages |
| 5 | Claude Code instructions and skills valid | ✅ Checked against current docs (code.claude.com/docs/en/skills, /memory, /settings). All 5 `SKILL.md` and 3 rule files have parseable YAML frontmatter; skill `name` equals directory name; descriptions 266–385 chars (limit 1,536); rules use the `paths` field; CLAUDE.md is 78 lines (guideline < 200); `.claude/settings.json` is valid JSON |
| 6 | `.gitignore` prevents sensitive files | ✅ Tested with `git check-ignore` in a scratch repo: `.wav`, `.mp3`, `.flac` (incl. under `backend/tests/`), `.env`, `.env.local`, `data/`, `.sqlite`, private keys ignored; `.env.example` and docs not ignored. `check_staged.sh` tested: blocks a force-added `.wav`, `.env`, and an AWS-style key; passes a clean staging area |
| 7 | Roadmap achievable for a small team | ✅ with caveats: nine milestones with a thin vertical slice first; no dates (velocity unknown); ASR, segmentation, resumable upload, lexicon deferred. Main schedule risk is governance answers (Q-L*), not engineering |
| 8 | Mermaid diagrams render | ✅ 15 diagrams parsed with mermaid 11 |
| 9 | Internal links | ✅ No broken relative links between docs |
| 10 | Technical claims checked | ✅ FFmpeg commands smoke-tested on synthetic audio (FFmpeg 6.1); Python 3.13 Unicode 15.1 includes Nag Mundari; Nag Mundari block U+1E4D0–U+1E4FF (Unicode 15.0); PostgreSQL 18 `uuidv7()`; MinIO CE no longer distributed upstream; DPDP Rules notified 13 Nov 2025 |

## 3. Not yet validated (by design)

Real-device recording formats (Q-T1), Opus on iOS Safari (Q-T2), contributor bundle size, Procrastinate fit, Chromaprint on speech (Q-T5), Nag Mundari fonts on target phones (Q-T6), cost figures (ranges only).

## 4. Open questions that block the pilot

Q-L1 ownership/data steward · Q-L2 IP policy and funder terms · Q-L3 ethics approval · Q-L4 minors · Q-L8 DPDP research exemption · Q-P4 repository visibility and ownership. Full list: [ASSUMPTIONS_AND_OPEN_QUESTIONS.md](ASSUMPTIONS_AND_OPEN_QUESTIONS.md).

## 5. Repository and Git findings

| Finding | Impact | Needed from owner |
|---------|--------|-------------------|
| `AyushSoni3398/lokdhara` is **public**; the brief requires private unless approved | Planning docs (no data) would be public once pushed | Decide visibility with AyushSoni3398 (only the owner can change it) |
| Claude's GitHub connection for this session is a different account without push permission on `AyushSoni3398/lokdhara` | Cannot push from this environment | Owner pushes the prepared branch from their own machine (bundle in project files) |
| Configured git author in the working environment was a generic bot identity | Commits would not be attributed to the owner | Owner re-authors the commits with their own git identity before pushing; no AI co-author trailers |

## 6. Files created or changed

- **Changed:** `README.md` (kept original vision paragraph; added MVP focus, status, reading guide).
- **Created (repo root):** `CLAUDE.md`, `.gitignore`, `.editorconfig`, `.env.example`.
- **Created (`.claude/`):** `settings.json`; rules `backend-python.md`, `frontend.md`, `migrations.md`; skills `audio-data-pipeline`, `mundari-text-processing`, `database-design`, `privacy-review`, `git-workflow` (+ `scripts/check_staged.sh`).
- **Created (`docs/`):** PRODUCT_REQUIREMENTS, USER_PERSONAS, USER_FLOWS, MVP_SCOPE, ASSUMPTIONS_AND_OPEN_QUESTIONS, TECH_STACK_EVALUATION, SYSTEM_ARCHITECTURE, ARCHITECTURE_DIAGRAM, ARCHITECTURE_DECISIONS, INFRASTRUCTURE_AND_COSTS, DATA_LIFECYCLE, AUDIO_PROCESSING_PIPELINE, TEXT_PROCESSING_PIPELINE, DATA_DICTIONARY, DATABASE_SCHEMA, DATASET_VERSIONING, DATA_QUALITY_AND_VALIDATION, PRIVACY_AND_SECURITY, CONSENT_AND_DATA_GOVERNANCE, ACCESS_CONTROL, DATA_RETENTION_AND_DELETION, API_SPECIFICATION, TESTING_STRATEGY, DEPLOYMENT, OBSERVABILITY_AND_BACKUPS, ROADMAP, PLANNING_REVIEW.

Deliberately **not** created: `backend/`, `frontend/`, `infra/`, CI workflows (Milestone 1, after approval); a `testing-and-quality` skill (its content is covered by CLAUDE.md, TESTING_STRATEGY, and the path-scoped rules; a skill adds value once test commands exist — revisit at M1).

## 7. Commits

Eleven commits on `docs/planning-foundation`, no AI trailers, to be pushed by the repository owner (§5):

1. `chore: add repository safety ignores and editor conventions`
2. `docs: define Lokdhara MVP requirements, personas, flows, and scope`
3. `docs: evaluate technology stack and record architecture decisions`
4. `docs: design language-data lifecycle and processing pipelines`
5. `docs: propose database schema, data dictionary, and dataset versioning`
6. `docs: document consent, privacy, access control, and retention`
7. `docs: specify API, testing, deployment, and backups`
8. `docs: add implementation roadmap`
9. `chore: add Claude Code project instructions, rules, and skills`
10. `docs: update README for Mundari MVP focus`
11. `docs: add planning review`

## 8. Decisions requiring the project owner's approval

1. Approve (or amend) the primary stack and ADR-001–017.
2. Approve the MVP scope boundary and the "no minors in pilot" default.
3. Push the branch from the owner's machine under the owner's git identity (§5).
4. Decide repository visibility with the owner (Q-P4).
5. Approve starting Milestone 1.

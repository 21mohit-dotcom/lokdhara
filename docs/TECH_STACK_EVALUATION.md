# Technology Stack Evaluation

Status: **Recommendation for approval** · Evidence checked 2026-10-11. Versions and prices change; re-verify before Milestone 1 and record changes in [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md).

## 1. How choices were judged

Each option was scored against the constraints in the project brief, in this order of weight:

1. **Fit for the data** — relational integrity between speakers, consent, recordings, text revisions, reviews, and releases.
2. **Small-team maintainability** — few languages, few moving parts, good documentation, large pool of answers when students get stuck.
3. **Audio/NLP ecosystem** — how naturally the stack connects to audio tooling and future research pipelines.
4. **Low-bandwidth delivery** — how small and cacheable the contributor-facing pages can be.
5. **Cost** — can it run on one small server or institutional hardware.
6. **Reversibility** — how painful it would be to change later.

Popularity was not a criterion on its own.

## 2. Recommended primary stack (summary)

| Layer | Choice | Key reason |
|-------|--------|-----------|
| Frontend | **React + TypeScript, built with Vite**, as a static single-page app (PWA-ready) | Static files are cheap to host and cache; no server rendering needed for private, signed-in pages. |
| Backend | **Python 3.13 + FastAPI**, SQLAlchemy 2, Alembic, Pydantic v2 | One language for API, audio processing, and research tooling. |
| Database | **PostgreSQL 18** with JSONB for extensible metadata | Relational integrity + flexible metadata + full-text and trigram search in one system. |
| File storage | **S3-compatible object storage** behind a storage interface; local filesystem adapter in development | Portable between providers and institutional storage. |
| Background jobs | **PostgreSQL-backed queue** (Procrastinate preferred; in-house `SKIP LOCKED` table as fallback), separate worker process | No Redis or broker to run. |
| Auth | **Invite-only accounts, server-side sessions in HttpOnly cookies, Argon2id hashes, role-based access + consent-based filtering** | Simple, revocable, no third-party identity dependency. |
| Audio tooling | **FFmpeg/ffprobe** (deterministic), optional **Silero VAD** as advisory | Mature, scriptable, version-pinnable. |
| Deployment | **Docker Compose on one VM** (or institutional server) with **Caddy** for HTTPS | Smallest operable footprint. |
| CI | **GitHub Actions**: lint, type-check, tests, secret scan, forbidden-file check | Free for this scale; already where the code lives. |

The rest of this document shows the comparisons behind each row.

## 3. Frontend

| Criterion | React + Vite (SPA) | Next.js (React framework) | SvelteKit | Server-rendered templates (FastAPI + HTMX) |
|-----------|-------------------|---------------------------|-----------|-------------------------------------------|
| Hosting | Static files behind Caddy/CDN | Needs a Node server for SSR/server actions, or static export with limits | Node adapter or static | Same server as API |
| Bundle size for contributors | Moderate; controllable with code-splitting | Similar client React cost plus framework runtime | Smallest client bundles | Smallest (mostly HTML) |
| Browser audio recording, IndexedDB drafts, waveform UI | Natural in client JS | Same, but SSR adds friction ("use client" boundaries) | Natural | Possible but awkward; needs substantial JS anyway |
| Student familiarity / help available | Very high | High | Medium | Medium |
| SEO / public pages | Not needed for MVP (all pages private) | Strong | Strong | Strong |
| Second runtime in production | No | **Yes (Node)** | Yes unless static | No |

**Decision: React + TypeScript + Vite SPA.** Lokdhara's pages are signed-in and interactive (recording, drafts, review editor), so server rendering buys little and adds a second production runtime. SvelteKit would give smaller bundles, but fewer students know it; the bundle budget (NFR-1) is achievable with React through route-level code splitting and avoiding heavy UI kits. HTMX is attractive for low bandwidth but the recording/draft/review features need substantial client JavaScript regardless.

Supporting libraries (to confirm in M1): React Router, TanStack Query (server state), react-i18next (UI translations), Vitest + Testing Library, Playwright (E2E), ESLint + Prettier. `vite-plugin-pwa` later if offline caching is needed.

**Change this decision if:** a public, SEO-dependent website becomes a goal (consider Next.js or a separate static site for public pages), or field tests show the SPA is too heavy on target phones (consider Preact compatibility mode or HTMX for contributor pages).

Docs: [Vite](https://vite.dev/guide/), [React](https://react.dev/), [MediaRecorder (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder).

## 4. Backend

| Criterion | Python + FastAPI | Node.js + Fastify | Node.js + Express | Python + Django (+ DRF) |
|-----------|------------------|-------------------|-------------------|-------------------------|
| Audio/NLP ecosystem | **Best**: same language as soundfile, Silero VAD, Hugging Face, research notebooks | Shells out to FFmpeg; ML needs a Python sidecar | Same as Fastify | Best (Python) |
| Languages in the codebase | Python (backend) + TS (frontend) | TS everywhere | TS everywhere | Python + TS |
| Typed request/response validation and OpenAPI | Built in (Pydantic) | Built in (JSON Schema) | Add-ons | DRF serializers; OpenAPI via add-ons |
| Built-in admin UI | No | No | No | **Yes** (Django admin) |
| Async I/O for uploads | Yes | Yes | Partial | Partial (async views exist; ORM mostly sync) |
| Boilerplate | Low | Low | Low | Higher but "batteries included" |

**Decision: Python 3.13 + FastAPI.** The decisive factor is that audio validation, quality metrics, dataset export, and any future speech/NLP work are Python-first. A Node backend would very likely need a Python worker anyway, making two backend languages for a small team. FastAPI gives typed contracts and generated OpenAPI docs that the frontend can consume.

**Django was the closest alternative.** Its admin site would save effort on admin screens. We chose FastAPI because the API-first SPA design, explicit SQLAlchemy models, and Alembic migrations give clearer control over immutable/versioned tables, and the admin screens Lokdhara needs (withdrawals, jobs, consent forms) are workflow-specific anyway. **Change to Django if** the team finds itself rebuilding generic CRUD admin screens repeatedly by M6.

Supporting libraries: SQLAlchemy 2.x (ORM + Core), Alembic (migrations), Pydantic v2 + pydantic-settings, psycopg 3, argon2-cffi, `cryptography` (AES-GCM for speaker identity fields), python-multipart (uploads), boto3 (S3 API), `regex` (Unicode script properties), uv (dependency management), ruff (lint/format), mypy, pytest + httpx.

Docs: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/), [Alembic](https://alembic.sqlalchemy.org/), [Pydantic](https://docs.pydantic.dev/).

## 5. Database

The data model (see [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)) is dominated by **relationships that must stay correct**: a translation belongs to a specific transcript revision, which belongs to a recording, which belongs to a submission tied to a speaker and a consent record; a dataset release references exact revisions. Withdrawals must propagate through all of them.

| Requirement | PostgreSQL | MongoDB |
|-------------|-----------|---------|
| Foreign keys and cascading rules (speaker → consent → submissions → releases) | Native, enforced | Application-enforced only |
| Multi-table transactions (approve + write audit log + update status atomically) | Native | Supported (replica set) but less idiomatic |
| Flexible linguistic metadata | JSONB columns with GIN indexes and optional JSON schema checks | Native documents |
| Immutability guarantees | Triggers / privileges can block UPDATE/DELETE on revision and audit tables | Application-level |
| Search | Full-text search (`simple` config, no stemming needed) + `pg_trgm` for fuzzy matching in any script | Text indexes; Atlas Search is a managed add-on |
| Research exports | SQL joins, `COPY`, easy to reason about | Aggregation pipelines |
| Future NLP integration | Tables export cleanly to Parquet/CSV/JSONL; pgvector available if embeddings are ever needed | Possible |
| Team familiarity | High (taught in most courses) | Medium |

**Decision: PostgreSQL 18.** It gives enforced integrity for consent propagation, and JSONB covers the genuinely flexible parts (collection context, dialect notes, extra linguistic attributes) without giving up constraints elsewhere. PostgreSQL 18 also provides a built-in `uuidv7()` function for time-ordered IDs. **Change if:** never likely for the core; a separate search engine (e.g., OpenSearch) could be added later only if Postgres search proves insufficient at measured scale.

Docs: [PostgreSQL 18](https://www.postgresql.org/docs/18/), [JSONB](https://www.postgresql.org/docs/18/datatype-json.html), [pg_trgm](https://www.postgresql.org/docs/18/pgtrgm.html), [Full text search](https://www.postgresql.org/docs/18/textsearch.html).

## 6. Audio and file storage

| Option | Pros | Cons |
|--------|------|------|
| Local disk on the server | Free, simple | Single point of failure; backups are manual; ties data to one machine |
| AWS S3 (incl. Mumbai region) | Mature, versioning, object lock, lifecycle rules, India region | Egress fees; more complex IAM |
| Cloudflare R2 | S3 API, no egress fees, small free tier | Region control is coarser; check residency needs |
| Backblaze B2 | Low storage price, S3 API | Fewer regions |
| Institutional storage (S3-compatible or NFS) | Possibly free, may satisfy residency/IP policy | Depends on IT support |
| Self-hosted MinIO for dev | Previously the default S3 emulator | **MinIO Community Edition is no longer distributed as maintained binaries/images upstream** (source-only, maintenance mode since late 2025), so it is not recommended for new projects. |

**Decision:** Code talks to an internal `ObjectStore` interface with two adapters: **local filesystem** (development, tests) and **S3-compatible** (staging/production). The production provider is chosen in M8 after Q-L7 (data residency) and Q-P5 (budget). Buckets are separated by sensitivity: `originals`, `derived`, `consent-evidence`, `exports` (see [PRIVACY_AND_SECURITY.md](PRIVACY_AND_SECURITY.md)). For S3-adapter integration tests, a lightweight S3-compatible server (candidates: SeaweedFS, Garage) or a mocking library will be evaluated in M2.

Uploads go **through the API** into a quarantine area in MVP (not direct browser-to-bucket presigned uploads), so validation and rate limiting happen in one place. Presigned direct upload is a scaling option later.

## 7. Authentication and authorisation

| Option | Pros | Cons |
|--------|------|------|
| **Server-side sessions (opaque token in HttpOnly, Secure, SameSite cookie; session rows in Postgres)** | Instantly revocable, no tokens in JS, simple | CSRF protection needed for state-changing requests |
| JWT access + refresh tokens | Stateless | Hard to revoke; easy to misuse; stored in JS → XSS exposure |
| Managed auth (Auth0, Clerk, Supabase Auth, Firebase) | Less code; MFA/OTP built in | External processor of personal data; cost at scale; vendor lock-in; data-residency questions |
| Institution SSO (SAML/OIDC) | Good for staff/researchers | Community contributors won't have institutional accounts |
| Phone OTP | Familiar to users in India | SMS cost, SIM-swap risk, third-party SMS provider handles phone numbers |

**Decision:** Invite-only accounts with username/password, **Argon2id** hashing, server-side sessions, CSRF token for unsafe methods, rate-limited login. Authorisation is **two layers**: role permissions (what actions a role may take) and **data-level filtering by effective consent and restriction flags** (which items a user may see). Details in [ACCESS_CONTROL.md](ACCESS_CONTROL.md). **Change if:** the institution offers OIDC for staff (add it for reviewers/researchers), or field tests show passwords are unworkable for contributors (consider facilitator-only submission or phone OTP after a cost/privacy review).

References: [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

## 8. Data processing

| Task | Tool | Kind |
|------|------|------|
| Container/codec detection, duration, sample rate, channels | `ffprobe` | Deterministic |
| File signature check | Magic-byte table in code + successful full decode by FFmpeg | Deterministic |
| Format conversion, resampling, loudness/peak/clipping stats, silence detection | `ffmpeg` (`aresample`, `astats`, `ebur128`, `silencedetect`) | Deterministic (given pinned version) |
| Exact duplicate detection | SHA-256 of original bytes; SHA-256 of decoded PCM for re-encoded copies | Deterministic |
| Near-duplicate detection | Chromaprint (`fpcalc`) — designed for music, **unproven on speech** | Heuristic; experiment only (Q-T5) |
| Voice activity detection | Silero VAD (small neural model) or WebRTC VAD | Model-based; **advisory only** |
| Unicode normalisation, script detection | Python `unicodedata` (NFC), `regex` (`\p{Script=…}`) | Deterministic |
| Transcription assistance (ASR) | Candidates to *evaluate* later: Meta MMS (check whether a Mundari checkpoint exists and note its non-commercial licence), community fine-tunes. Whisper's published language list does not include Mundari. | Model-generated; **never ground truth** (ADR-014) |
| Machine translation | Candidates to evaluate later (e.g., multilingual MT models covering Indic languages) | Model-generated; same rule |

Every processing step records the tool name and version in the database so results are reproducible.

## 9. Deployment and operations

| Option | Monthly cost (pilot, rough) | Ops effort | Notes |
|--------|------------------------------|-----------|-------|
| **One VM + Docker Compose (Caddy, API, worker, Postgres)** + external object storage | Low (see [INFRASTRUCTURE_AND_COSTS.md](INFRASTRUCTURE_AND_COSTS.md)) | Medium: OS updates, backups | Recommended. Same Compose file locally and in production. |
| Institutional server | Possibly zero | Depends on IT | Preferred if available and policy-compliant. |
| PaaS (Render, Railway, Fly.io) + managed Postgres | Low–medium, grows with usage | Low | Good fallback; check residency and FFmpeg availability in worker images. |
| Kubernetes / microservices | High | High | Rejected for MVP (ADR-002). |

Backups: nightly encrypted `pg_dump` to a separate bucket, object versioning on `originals`, quarterly restore drill. Monitoring: structured JSON logs, health endpoint, external uptime check, optional error tracker (e.g., Sentry free tier) with PII scrubbing. See [OBSERVABILITY_AND_BACKUPS.md](OBSERVABILITY_AND_BACKUPS.md).

## 10. Version baseline (verify at M1)

| Component | Target | Reason |
|-----------|--------|--------|
| Python | 3.13 | Mature, wide wheel support; move to newer after libraries confirm support. |
| Node.js (build tooling only) | Current Active LTS (24.x at time of writing) | Vite toolchain. |
| PostgreSQL | 18 | Current major with a year of patch releases; `uuidv7()`. |
| FFmpeg | Distribution package pinned in the Docker image; version recorded per job | Reproducibility. |

## 11. What has *not* been validated yet

- Real-device recording formats and decode reliability (Q-T1).
- Opus playback on iOS Safari (Q-T2).
- Bundle size of the contributor flow against the 250 KB target (measured in M3).
- Procrastinate's fit vs. a minimal in-house queue (spike in M2). *Done: in-house chosen, see ADR-019.*
- Any ASR/MT model quality on Mundari (out of MVP scope).

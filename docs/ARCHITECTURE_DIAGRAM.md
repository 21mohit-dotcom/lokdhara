# Architecture Diagrams

All diagrams are Mermaid and render on GitHub. They describe the **proposed** architecture in [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

## 1. Context

```mermaid
flowchart LR
    C[Contributor / Facilitator<br/>Android phone] -->|HTTPS| L((Lokdhara))
    R[Reviewer<br/>laptop] -->|HTTPS| L
    S[Researcher] -->|HTTPS| L
    A[Administrator] -->|HTTPS| L
    L -->|S3 API| O[(Object storage)]
    L -->|backups| B[(Backup bucket<br/>separate credentials)]
    G[Governance: professor, institution,<br/>community representatives] -. decisions .-> A
```

## 2. Containers

```mermaid
flowchart TB
    subgraph Client
        SPA[React SPA<br/>IndexedDB drafts<br/>MediaRecorder]
    end
    subgraph Server["Single VM (Docker Compose)"]
        P[Caddy<br/>TLS, static files,<br/>size limits]
        API[FastAPI api process]
        W[Worker process<br/>ffmpeg / ffprobe]
        DB[(PostgreSQL 18<br/>data + job queue + audit)]
    end
    subgraph Storage["Object storage (S3-compatible)"]
        Q[quarantine/]
        OR[originals/ write-once]
        DV[derived/]
        CE[consent-evidence/ restricted]
        EX[exports/ short-lived]
    end
    SPA -->|/api/*| P --> API
    SPA -->|static| P
    API --> DB
    W --> DB
    API -->|stream upload| Q
    W -->|validate, promote| OR
    W --> DV
    W --> EX
    API -->|consent evidence| CE
    SPA -.->|signed URL playback| DV
```

## 3. Submission state machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> uploading: submit
    uploading --> processing: upload complete
    uploading --> draft: upload failed (client keeps draft)
    processing --> accepted: every check ok
    processing --> rejected_invalid: validation failed
    processing --> processing_failed: job dead after retries
    processing_failed --> processing: admin re-queue
    draft --> withdrawn
    accepted --> withdrawn
    withdrawn --> [*]
```

There is no human review step ([ADR-021](ARCHITECTURE_DECISIONS.md#adr-021--no-human-reviewer-accept-after-automatic-checks-keep-text-unverified)). The statuses `awaiting_review`, `in_review`, `changes_requested`, `approved` and `rejected` are still allowed by the database but unused, kept for later peer checking. An admin hides a reported item with a restriction flag, not a status.

`uploading` happens on the device: the server keeps a submission in `draft` while its recording uploads, and `submit` moves it straight to `processing` (docs/API_SPECIFICATION.md §4).

Restriction (`sensitive`, `third_party_voice`, `contains_pii`, `culturally_restricted`) is a **separate flag set**, not a state, because an accepted item can also be restricted (hidden).

## 4. Effective access computation

```mermaid
flowchart LR
    CR[Active consent record<br/>per-use permissions] --> E{Effective permissions}
    RS[Restriction flags<br/>set by reviewers] --> E
    ST[Submission status<br/>must be approved] --> E
    E --> V[Who may view]
    E --> D[Which dataset purposes may include it]
    U[User role + scopes] --> V
```

Effective permission = the **most restrictive** of consent, restriction flags, and status. Nothing can widen what the speaker consented to.

## 5. Entity relationships (summary)

Full schema: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

```mermaid
erDiagram
    USER ||--o{ USER_ROLE : has
    USER ||--o{ SUBMISSION : submits
    SPEAKER ||--o| SPEAKER_IDENTITY : "restricted details"
    SPEAKER ||--o{ CONSENT_RECORD : gives
    CONSENT_FORM ||--o{ CONSENT_RECORD : "version used"
    SPEAKER ||--o{ SUBMISSION : "voice/text of"
    CONSENT_RECORD ||--o{ SUBMISSION : covers
    SUBMISSION ||--o{ RECORDING : contains
    RECORDING ||--o{ RENDITION : derived
    SUBMISSION ||--o{ TEXT_LAYER : contains
    RECORDING ||--o{ TEXT_LAYER : "transcribed by"
    TEXT_LAYER ||--o{ TEXT_LAYER : "translated by"
    TEXT_LAYER ||--o{ TEXT_REVISION : versions
    SUBMISSION ||--o{ REVIEW_EVENT : reviewed
    DATASET_RELEASE ||--o{ DATASET_RELEASE_ITEM : freezes
    DATASET_RELEASE_ITEM }o--|| SUBMISSION : includes
    DATASET_RELEASE ||--o{ EXPORT_REQUEST : exported
```

## 6. Processing pipeline

```mermaid
flowchart LR
    U[Upload to quarantine<br/>sha256 + magic bytes] --> J1[job: audio.validate<br/>ffprobe + full decode]
    J1 -->|ok| P[Promote to originals/<br/>write-once]
    J1 -->|fail| X[rejected_invalid<br/>reason recorded]
    P --> J2[job: audio.analyze<br/>astats, ebur128, silencedetect]
    P --> J3[job: audio.renditions<br/>playback Opus, analysis FLAC 16k mono]
    P --> J4[job: audio.dedupe<br/>hash match]
    J2 --> R[accepted]
    J3 --> R
    J4 --> R
```

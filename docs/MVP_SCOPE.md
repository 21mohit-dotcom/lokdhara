# MVP Scope

Status: **Draft for approval**

## The one-sentence MVP

> An invite-only web app where facilitators and contributors submit consented Mundari audio and text, reviewers verify and correct it, and authorised researchers build versioned, consent-filtered datasets from approved items.

## In scope

| Area | Included in MVP | Requirement IDs |
|------|-----------------|-----------------|
| Accounts | Invite-only accounts, five roles, admin-assisted password reset | FR-A1–A5 |
| Languages of UI | Hindi and English; strings externalised for Mundari later | FR-A7, NFR-4 |
| Speakers | Pseudonymous speaker profiles; optional restricted identity details | FR-C1–C2 |
| Consent | Versioned forms, per-use permissions, three capture methods, guardian consent, withdrawal | FR-C3–C7 |
| Submissions | Audio (record/upload), text entries, transcription, Hindi/English translation, metadata, on-device drafts | FR-S1–S7 |
| Processing | Signature + decode validation, technical metadata, playback and analysis renditions, quality signals, exact-duplicate detection, text Unicode normalisation | FR-P1–P8 |
| Review | Queue, playback, revisions, approve/reject/request-changes/restrict | FR-R1–R5 |
| Datasets | Search approved items, frozen releases, export package with manifest + data card | FR-D1–D5 |
| Admin | Users/roles, consent forms, withdrawals, failed jobs, audit log | FR-X1–X2 |
| Ops | Single-server deployment, backups, restore test, basic monitoring | NFR-9 |

## Explicitly out of scope for the MVP

| Item | Why excluded | Revisit when |
|------|--------------|--------------|
| Recipes, artefacts, traditions, general heritage catalogue | Brief limits MVP to language preservation; different data model and consent questions. | After a successful language pilot. |
| ASR / automatic transcription | No validated Mundari model; risk of unverified output treated as truth; cost. | After a reviewed dataset exists to evaluate candidates (see ADR-014). |
| Machine translation | Same as ASR. | Same. |
| Public anonymous browsing / public website of recordings | Requires community and institutional approval of public access; needs governance first. | After Q-G1/Q-L1 are resolved. |
| Open self-registration | Abuse and consent-quality risk during pilot. | After moderation capacity is proven. |
| Native Android/iOS apps | Web app + on-device drafts covers MVP; separate codebase is too costly. | If field testing shows the browser approach fails. |
| Fully offline-first app (service-worker sync of everything) | Complexity; drafts-on-device covers the main loss case. | Milestone after pilot if needed. |
| Time-aligned segmentation UI | Valuable but large; schema reserves space. | Post-MVP milestone. |
| Lexicon / dictionary module with headwords, senses | Different data model; words are collected as text entries first. | Post-MVP. |
| Two-reviewer consensus workflow | Pilot has few reviewers. | When reviewer pool grows. |
| Audio redaction tools | Complex; restrict instead. | Post-MVP. |
| SMS/WhatsApp integrations, payments, gamification | Not needed for the core goal. | — |
| Microservices, Kubernetes, message brokers | Overengineering for a small team (ADR-002, ADR-007). | Only with measured scaling need. |

## MVP is "done" when

1. All Milestone 0–8 acceptance criteria in [ROADMAP.md](ROADMAP.md) pass.
2. A pilot group (size agreed with the supervisor) has submitted, reviewed, and released at least one dataset end to end.
3. The blocking open questions in [ASSUMPTIONS_AND_OPEN_QUESTIONS.md](ASSUMPTIONS_AND_OPEN_QUESTIONS.md) (marked **Blocks pilot**) are answered and recorded.

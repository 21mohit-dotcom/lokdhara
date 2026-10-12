# lokdhara
Lokdhara is a community-driven platform for preserving and digitizing linguistic and cultural heritage. It enables communities to contribute indigenous languages, speech, stories, songs, traditions, recipes, artifacts, and cultural knowledge, creating structured digital collections for preservation, research, and future technological applications.

## Current focus: Mundari language preservation (MVP)

The first version focuses **only on the Mundari language** (Jharkhand, India): consented audio recordings from native speakers, Mundari text, transcriptions linked to recordings, Hindi and English translations, human review, and versioned datasets released only within the permissions speakers have granted. The wider heritage vision above is long-term and out of scope for the MVP (see [docs/MVP_SCOPE.md](docs/MVP_SCOPE.md)).

## Project status

**Milestone 1 (application skeleton).** The plan was approved on 2026-10-11. The app does not collect anything yet, and **no community data is stored in this repository — ever** (audio, collected text, consent records, and datasets live only in access-controlled storage).

## Where to start reading

| If you want to… | Read |
|-----------------|------|
| Understand what we are building | [Product requirements](docs/PRODUCT_REQUIREMENTS.md), [MVP scope](docs/MVP_SCOPE.md), [User flows](docs/USER_FLOWS.md) |
| See the chosen stack and why | [Tech stack evaluation](docs/TECH_STACK_EVALUATION.md), [Architecture decisions](docs/ARCHITECTURE_DECISIONS.md) |
| Understand the system | [System architecture](docs/SYSTEM_ARCHITECTURE.md), [Diagrams](docs/ARCHITECTURE_DIAGRAM.md) |
| Work with the data model | [Data lifecycle](docs/DATA_LIFECYCLE.md), [Database schema](docs/DATABASE_SCHEMA.md), [Data dictionary](docs/DATA_DICTIONARY.md) |
| Understand consent and privacy | [Consent and governance](docs/CONSENT_AND_DATA_GOVERNANCE.md), [Privacy and security](docs/PRIVACY_AND_SECURITY.md), [Access control](docs/ACCESS_CONTROL.md) |
| Know what happens next | [Roadmap](docs/ROADMAP.md), [Planning review](docs/PLANNING_REVIEW.md), [Open questions](docs/ASSUMPTIONS_AND_OPEN_QUESTIONS.md) |
| Test, measure, or deploy it | [Testing strategy](docs/TESTING_STRATEGY.md), [Load testing](docs/LOAD_TESTING.md), [Deployment](docs/DEPLOYMENT.md), [Recording modes](docs/RECORDING_MODES.md) |

## Stack

React + TypeScript + Vite (frontend) · Python + FastAPI (backend and audio worker) · PostgreSQL · S3-compatible object storage · FFmpeg · Docker Compose.

## Contributing

- Read [CLAUDE.md](CLAUDE.md) for project rules (they apply to humans and AI assistants alike).
- Conventional Commits, small focused changes, feature branches.
- Never commit recordings, personal data, consent documents, datasets, `.env` files, or credentials.

## Development setup

You need Git, Docker, Python 3.13 with [uv](https://docs.astral.sh/uv/), and Node.js 24.

```bash
cp .env.example .env                                   # local values only; never commit .env
docker compose -f infra/docker-compose.yml up -d db    # PostgreSQL 18
cd backend && uv sync && uv run uvicorn app.main:app --reload   # http://localhost:8000/healthz
cd frontend && npm ci && npm run dev                    # http://localhost:5173
```

Details: [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md). CI runs lint, type checks, tests, a bundle-size budget, a forbidden-file check, and a secret scan on every pull request.

## Licence

Not yet decided (open questions Q-L5 and Q-L6). Until a licence is chosen, all rights are reserved by the project owners.

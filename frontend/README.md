# Lokdhara frontend

React + TypeScript + Vite single-page app (ADR-003). UI in Hindi and English (`src/i18n/locales/`).

```bash
npm ci            # install
npm run dev       # http://localhost:5173 (proxies /api to the backend on :8000)
npm run lint && npm run typecheck && npm test
npm run build && npm run size   # production build + gzip size budget (250 KB)
npm run e2e       # browser tests against the real API (see below)
```

Every visible string goes in both `hi.json` and `en.json`; a test fails if the key sets differ.

## Layout

| Folder | What is in it |
|--------|---------------|
| `src/api/` | `fetch` wrapper (CSRF header, problem `code`s) and one function per API call |
| `src/auth/` | the session, sign-in and sign-out, `RequireAuth` |
| `src/drafts/` | drafts kept on the device in IndexedDB, and the upload that sends them step by step |
| `src/recording/` | browser recording (`MediaRecorder`, no transcoding) and file choice |
| `src/pages/` | one component per screen; `submission/` holds the steps of the contribution flow |
| `src/test/` | a fake API for component tests |
| `e2e/` | Playwright tests of the whole flow |

A draft is saved on the device at every step and stays there until the server has all of it.
Uploads retry by themselves when the connection comes back (docs/SYSTEM_ARCHITECTURE.md §4.1).

## Browser tests

`npm run e2e` starts the API and the dev server (or reuses ones already running), migrates the
database, runs `seed-dev` for the test consent forms and prompts, and creates a new admin and
contributor with random passwords for each run. It needs PostgreSQL running
(`docker compose -f infra/docker-compose.yml up -d db`) and `uv sync` done in `backend/`.
Chromium gets a fake microphone that plays a tone; all text typed is synthetic.

The tests use your local development database. If the installed Chromium does not match the
Playwright version, point to it with `PLAYWRIGHT_CHROMIUM_PATH=/path/to/chrome npm run e2e`, or
run `npx playwright install chromium`.

# Lokdhara frontend

React + TypeScript + Vite single-page app (ADR-003). UI in Hindi and English (`src/i18n/locales/`).

```bash
npm ci            # install
npm run dev       # http://localhost:5173 (proxies /api to the backend on :8000)
npm run lint && npm run typecheck && npm test
npm run build && npm run size   # production build + gzip size budget (250 KB)
```

Every visible string goes in both `hi.json` and `en.json`; a test fails if the key sets differ.

---
paths:
  - "frontend/**/*.{ts,tsx,css}"
---

# Frontend (React / TypeScript / Vite) conventions

- Every user-visible string goes through react-i18next; add keys to both `hi` and `en` catalogues in the same change.
- Low-bandwidth budget: contributor flow ≤ 250 KB compressed JS+CSS. Code-split by route; no heavy UI kits or icon packs; check bundle report before adding a dependency.
- Mobile first (360 px wide), large touch targets, icons always paired with text.
- Never use `dangerouslySetInnerHTML`. Render user text as text.
- The SPA never decides access; hide controls only for convenience. The server is authoritative.
- Recordings and drafts are saved to IndexedDB before upload; never discard a recording because an upload failed.
- Do not transcode audio in the browser; upload the recorded blob as-is.
- No third-party analytics, trackers, or CDNs that receive user data.

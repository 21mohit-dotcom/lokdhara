# Infrastructure and Costs

Status: **Estimate for planning.** Prices below are rough ranges for orientation only, checked against no live price list; verify current pricing before committing to a provider. **No paid infrastructure is created during the planning phase.**

## 1. Environments

| Environment | Where | Data | Purpose |
|-------------|-------|------|---------|
| Local | Developer laptop, Docker Compose | Synthetic only | Development, tests |
| CI | GitHub Actions | Synthetic only | Lint, type-check, tests, scans |
| Staging | Small VM (or same VM, separate Compose project and database) | Synthetic or explicitly consented test recordings by team members | Release rehearsal, device testing |
| Production | VM or institutional server + object storage | Real, consented data | Pilot |

## 2. Storage volume model

Audio size depends heavily on the format contributors upload:

| Format | Approx. size per hour |
|--------|----------------------|
| WAV 44.1 kHz stereo 16-bit (field recorder) | ~635 MB |
| WAV 16 kHz mono 16-bit | ~115 MB |
| FLAC 16 kHz mono (analysis rendition) | ~50–80 MB |
| Browser Opus/WebM ~32 kbit/s (phone recording) | ~15 MB |
| Opus 24 kbit/s playback rendition | ~11 MB |

**Pilot assumption (A3):** 200 hours of audio in year one, mixed formats → originals ≈ 30–130 GB, plus derived ≈ 15–20 GB, plus backups. Plan for **≤ 300 GB total including backups** in year one.

## 3. Cost scenarios (monthly, rough)

| Item | Scenario A: institutional | Scenario B: low-cost cloud | Scenario C: managed PaaS |
|------|---------------------------|----------------------------|---------------------------|
| Compute (API + worker + Postgres) | ₹0 (institution) | 1 VM, 2 vCPU / 4 GB RAM: roughly US$10–25 | App + worker + managed Postgres: roughly US$25–60 |
| Object storage (≤ 300 GB) | ₹0 or internal recharge | roughly US$2–8 depending on provider | same as B |
| Egress | — | Low at pilot scale; zero on some providers | similar |
| Domain + DNS | ~US$10–15 per year | same | same |
| TLS | Free (Let's Encrypt via Caddy) | Free | Included |
| Error tracking | Free tier or self-hosted logs | Free tier | Free tier |
| **Total (approx.)** | **≈ ₹0–500** | **≈ US$15–35** | **≈ US$30–70** |

Recommendation: **Scenario A if the institution can provide a server and storage that meet policy; otherwise Scenario B in an Indian region if data residency is required (Q-L7).**

## 4. Cost risks and controls

| Risk | Control |
|------|--------|
| Large WAV uploads balloon storage | Upload limit (100 MB/file initially); encourage in-browser Opus recording; originals kept as uploaded. |
| Egress from researcher downloads | Exports are on request, time-limited, and audited. |
| Forgotten test buckets/VMs | All resources listed in [DEPLOYMENT.md](DEPLOYMENT.md) inventory; billing alerts on any paid account. |
| GPU costs for ASR | Out of MVP scope (ADR-014). |

## 5. Ownership of accounts

Paid accounts must be owned by the institution or project lead, not by an individual student's personal card, so the platform survives team changes (relates to Q-L1). Credentials are stored in a password manager shared with at least two maintainers, never in the repository.

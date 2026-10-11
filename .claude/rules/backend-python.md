---
paths:
  - "backend/**/*.py"
---

# Backend (Python / FastAPI) conventions

- Python 3.13, type hints everywhere; code must pass `ruff check`, `ruff format --check`, and `mypy`.
- Organise by domain module under `backend/app/modules/<module>/` with `models.py`, `schemas.py`, `service.py`, `router.py`. Routers stay thin: parse input, call a service, return a schema.
- Modules call each other's **service functions**, never each other's tables directly.
- Authorisation happens in services, not only in routers. Every list/search query must apply the effective-access predicate (`docs/ACCESS_CONTROL.md`).
- Use SQLAlchemy parameter binding only; never build SQL with f-strings.
- Errors are RFC 9457 problem details with a stable `code` (see `docs/API_SPECIFICATION.md`).
- Run external tools (ffmpeg, ffprobe) with argument lists via `subprocess.run([...], check=..., timeout=...)`, never `shell=True`.
- Logging: structured, no audio/text content, names, contacts, tokens, or raw IPs.
- Configuration only via `app/config.py` (pydantic-settings); never read `os.environ` elsewhere; never hard-code secrets.

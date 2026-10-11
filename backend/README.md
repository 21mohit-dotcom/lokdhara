# Lokdhara backend

FastAPI API (`app.main`) and background worker (`app.worker`) — see `docs/SYSTEM_ARCHITECTURE.md`.

```bash
uv sync                                   # install
uv run uvicorn app.main:app --reload      # API on http://localhost:8000 (docs at /api/docs)
uv run python -m app.worker               # worker (Ctrl+C to stop)
uv run pytest                             # tests
uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
```

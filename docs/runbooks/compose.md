# Docker Compose Runbook

## Prerequisites
- Docker and Docker Compose installed and running.
- Python 3.11+
- `uv`
- Optional local `.env` file at the project root. Start from `.env.example`.

Recommended variables:

```env
JWT_SECRET_KEY=change-me-for-local-dev
ADMIN_EMAIL=admin@example.com
DATABASE_URL=sqlite:///./app.db
REDIS_URL=redis://localhost:6379/0
```

## Launching the stack
To build and start the full stack locally:

```bash
docker compose up --build
```

Detached mode:

```bash
docker compose up -d --build
```

The API and worker both run Alembic migrations before starting their main process.

## Verifying the stack

### Health check
```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "version": "1.0.0"}
```

### Rate-limit headers
```bash
curl -i http://localhost:8000/plans
```

Check for:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`

### Frontend
Open:

- `http://localhost:8501`

### API docs
Open:

- `http://localhost:8000/docs`

### Worker logs
```bash
docker compose logs -f worker
```

### Redis health
```bash
docker compose exec redis redis-cli ping
```

Expected:

```text
PONG
```

## Running migrations manually
If you want to run the database setup outside Compose:

```bash
uv run python -m scripts.migrate
```

## Seeding sample data
```bash
uv run python scripts/seed.py
```

## Running tests locally
```bash
uv run pytest
```

Run only API tests:

```bash
uv run pytest tests/test_api.py
```

Run only worker tests:

```bash
uv run pytest tests/test_worker.py
```

Run only the Schemathesis contract tests:

```bash
uv run pytest tests/test_openapi.py
```

## Capturing the Redis trace excerpt required for EX3 notes
After the stack is healthy, inject a real Redis monitor excerpt into `docs/EX3-notes.md`:

```bash
uv run python scripts/capture_trace_excerpt.py
```

Before submission, confirm that `docs/EX3-notes.md` contains a **real** local excerpt.

## Resetting local state
```bash
docker compose down -v
rm -f app.db
```

## Submission hygiene
Do not submit or commit:

- `.env`
- `.venv/`
- `.pytest_cache/`
- `.hypothesis/`
- `app.db`

# Docker Compose Runbook

## Prerequisites
- Docker and Docker Compose installed and running.
- Python 3.11+
- `uv`
- Optional local `.env` file at the project root. Start from `.env.example`.

Recommended variables:

```env
GEMINI_API_KEY=
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
curl -i http://localhost:8000/courses
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
After the API container is up, seed sample users and courses from inside the running container:

```bash
docker compose exec api python scripts/seed.py
```

Or locally without Docker:

```bash
uv run python scripts/seed.py
```

## Running tests locally
Run all tests locally with `uv`:

```bash
uv run pytest
```

Run only the API tests:

```bash
uv run pytest tests/test_api.py
```

Run only the worker tests:

```bash
uv run pytest tests/test_worker.py
```

Run only the Schemathesis contract tests:

```bash
uv run pytest tests/test_openapi.py
```

## Running pytest and Schemathesis in CI
GitHub Actions CI is defined in `.github/workflows/ci.yml`.

The CI job performs these commands:

```bash
uv sync
uv run python -m scripts.migrate
uv run pytest tests/test_api.py
uv run pytest tests/test_worker.py
uv run pytest tests/test_openapi.py
```

Why this works in CI:
- the Alembic migration step creates the SQLite schema reproducibly,
- API tests validate auth, CRUD, role checks, and token-expiry behavior,
- worker tests validate retries/idempotency behavior,
- Schemathesis loads the ASGI app directly and validates public OpenAPI routes without needing a separately hosted server.

## Capturing the local service log excerpt for EX3 notes
After the stack runs locally, inject a real service log excerpt into `docs/EX3-notes.md`:

```bash
python scripts/capture_trace_excerpt.py
```

If your rubric specifically asks for a Logfire trace or a Redis trace visualization, replace the generated block with that capture before final submission.

## Resetting local state
If you want a clean local reset:

```bash
docker compose down -v
rm -f app.db
```

Then bring the stack up again.

## Submission hygiene
Do not submit or commit:
- `.env`
- `.venv/`
- `.pytest_cache/`
- `.hypothesis/`
- `app.db`

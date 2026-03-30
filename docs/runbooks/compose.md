# Docker Compose Runbook

## Purpose

This runbook explains how to launch, verify, and stop the local EX3 stack for EduBuilder.
The stack contains:

- `api`
- `frontend`
- `redis`
- `worker`

## 1. Launch the stack

From the repository root:

```bash
docker compose up --build
```

Expected local endpoints:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Frontend: `http://localhost:8501`
- Redis: `localhost:6379`

## 2. Verify service health

### API health endpoint

```bash
curl http://localhost:8000/health
```

Expected result: HTTP 200 and a JSON body with a healthy status.

### Frontend reachability

Open:

```text
http://localhost:8501
```

### Worker logs

```bash
docker compose logs -f worker
```

### Redis readiness

```bash
docker compose logs -f redis
```

## 3. Verify rate-limit headers

Run a public API request and inspect the headers:

```bash
curl -i http://localhost:8000/plans
```

Expected result: HTTP 200 plus rate-limit related headers exposed by the API.

## 4. Run migrations and seed data locally

If you want to prepare data outside Compose:

```bash
uv run python -m scripts.migrate
uv run python scripts/seed.py
```

## 5. Run automated tests

### Full pytest suite

```bash
uv run pytest
```

### API-focused tests

```bash
uv run pytest tests/test_api.py
```

### Worker tests

```bash
uv run pytest tests/test_worker.py
```

### Schemathesis / OpenAPI checks

```bash
uv run pytest tests/test_openapi.py
```

## 6. CI expectation

The repository CI should validate the same local story:

- migrations apply successfully,
- pytest passes,
- OpenAPI / Schemathesis checks pass.

## 7. Stop the stack

```bash
docker compose down
```

To remove local container state and volumes:

```bash
docker compose down -v
```

## 8. Capture the EX3 trace excerpt

Before final submission, run:

```bash
uv run python scripts/capture_trace_excerpt.py
```

Paste the generated output into `docs/EX3-notes.md`.

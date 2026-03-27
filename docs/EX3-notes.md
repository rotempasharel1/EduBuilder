# EX3 Notes – PoseAI Trainer

## 1. Final EX3 shape
PoseAI Trainer completes the EX1–EX3 progression as a tidy, local-first **squat coaching plan catalog** that combines:

- a FastAPI backend,
- SQLite persistence through SQLModel,
- a Streamlit user interface,
- Redis for rate limiting and worker coordination,
- and an async worker for background digest generation.

The system is intentionally scoped to stay understandable and runnable on one laptop.

## 2. Services in the local architecture

### 2.1 API service
Implemented in `poseai_backend/main.py`.

Responsibilities:

- authentication and authorization,
- plan CRUD,
- public/shared plan browsing,
- personal plan management,
- admin-only routes,
- health checks,
- Redis-backed rate-limit headers.

### 2.2 Persistence layer
Implemented with SQLite, SQLModel, and Alembic migrations.

Relevant files:

- `poseai_backend/database.py`
- `poseai_backend/models.py`
- `alembic/`
- `scripts/migrate.py`
- `scripts/seed.py`

### 2.3 Frontend service
Implemented in `frontend/app.py`.

Responsibilities:

- browse shared plans immediately,
- sign in or register,
- create and edit plans through the backend API,
- keep the main flows simple enough to demonstrate quickly.

### 2.4 Redis service
Redis is used for two focused EX3 tasks:

- API rate limiting,
- worker idempotency.

### 2.5 Worker service
Implemented in `scripts/refresh.py`.

Responsibilities:

- scan public plans,
- generate a weekly digest,
- retry transient failures,
- prevent duplicate work through Redis-backed idempotency keys,
- keep concurrency bounded.

## 3. Compose orchestration
The project includes `compose.yaml` with these services:

- `api`
- `frontend`
- `redis`
- `worker`

Start everything locally:

```bash
docker compose up --build
```

## 4. Verification steps

### 4.1 Health endpoint
```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "version": "1.0.0"}
```

### 4.2 Rate-limit headers
```bash
curl -i http://localhost:8000/plans
```

Expected headers include:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`

### 4.3 Frontend reachability
Open:

- `http://localhost:8501`

### 4.4 OpenAPI contract
Open:

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

## 5. Testing
Run all tests:

```bash
uv run pytest
```

Run only the contract check:

```bash
uv run pytest tests/test_openapi.py
```

Run only the worker tests:

```bash
uv run pytest tests/test_worker.py
```

Run only the API tests:

```bash
uv run pytest tests/test_api.py
```

## 6. Async refresher deliverable
The async refresher is implemented in `scripts/refresh.py` and provides:

- bounded concurrency via `anyio.CapacityLimiter`,
- retries for transient failures,
- Redis-backed idempotency keys,
- a `pytest.mark.anyio` worker test.

## 7. Security baseline
The project includes the required EX3 security baseline:

- hashed credentials,
- JWT-protected create/edit/delete flows,
- role/scope checks for admin-only endpoints,
- tests for expired tokens,
- tests for missing required scope.

### Token rotation steps
If a JWT secret is exposed locally:

1. change `JWT_SECRET_KEY` in `.env`,
2. restart the API service,
3. log in again to issue fresh tokens,
4. invalidate previously issued tokens by not reusing the old secret,
5. confirm protected endpoints now reject tokens signed with the old secret.

## 8. Enhancement
The EX3 enhancement is a **weekly public-plan digest** generated for public plans by the background worker.

This enhancement improves usability without increasing project scope too much.

## 9. Real local Redis trace excerpt
The helper script `scripts/capture_trace_excerpt.py` injects a real local **Redis monitor excerpt** into this file after a local Compose run.

Refresh the excerpt before submission:

```bash
uv run python scripts/capture_trace_excerpt.py
```

Important:

- do not submit the placeholder block below as the final artifact,
- only keep the generated block below after a successful local Compose run.

<!-- TRACE_EXCERPT_START -->

```text
Trace excerpt not refreshed yet.

Run:
uv run python scripts/capture_trace_excerpt.py

Expected result:
- Redis MONITOR lines appear here
- worker-trigger output appears here

Do not submit this placeholder block as the final EX3 artifact.
```

<!-- TRACE_EXCERPT_END -->

## 10. CI coverage
GitHub Actions is configured in `.github/workflows/ci.yml`.

The pipeline:

1. installs Python,
2. installs dependencies,
3. applies Alembic migrations,
4. runs API tests,
5. runs worker tests,
6. runs Schemathesis contract tests.

## 11. Submission hygiene
Before submitting, verify that the repository or ZIP does **not** include:

- `.env`
- `.venv/`
- `.pytest_cache/`
- `.hypothesis/`
- `app.db`

## 12. AI Assistance
AI tools were used as pair-programming aids for architecture, tests, runbooks, and documentation. All generated outputs should be validated locally by running the stack and tests before submission.

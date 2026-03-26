# EX3 Notes – EduBuilder

## 1. Final EX3 shape
EduBuilder completes the EX1–EX3 progression as a tidy, local-first **course builder and course catalog** that combines:
- a FastAPI backend,
- SQLite persistence through SQLModel,
- a Streamlit user interface,
- Redis for rate limiting and worker coordination,
- and an async worker for background digest generation.

The system is intentionally scoped to stay understandable and runnable on one laptop.

## 2. Services in the local architecture

### 2.1 API service
Implemented in `backend/main.py`.

Responsibilities:
- authentication and authorization,
- course CRUD,
- public/shared course browsing,
- personal course management,
- admin-only routes,
- AI-assisted course generation and draft endpoints,
- health checks,
- Redis-backed rate-limit headers.

### 2.2 Persistence layer
Implemented with SQLite, SQLModel, and Alembic migrations.

Relevant files:
- `backend/database.py`
- `backend/models.py`
- `alembic/`
- `scripts/migrate.py`
- `scripts/seed.py`

The EX3 database is reproducible through migrations plus seed data. SQLite artifacts are intentionally excluded from version control.

### 2.3 Frontend service
Implemented in `frontend/app.py`.

Responsibilities:
- browse shared courses immediately, even before signing in,
- sign in or register,
- create and edit courses through the backend API,
- trigger AI-assisted drafting,
- keep the main flows simple enough to demonstrate quickly.

### 2.4 Redis service
Redis is used for two focused EX3 tasks:
- API rate limiting,
- worker idempotency.

### 2.5 Worker service
Implemented in `scripts/refresh.py`.

Responsibilities:
- scan public courses,
- generate a weekly digest or recommendation summary,
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

Detached mode:

```bash
docker compose up -d --build
```

Stop the stack:

```bash
docker compose down
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
curl -i http://localhost:8000/courses
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
The EX3 enhancement is a **weekly digest / recommendation summary** generated for public courses by the background worker.

This enhancement improves usability without increasing project scope too much.

## 9. Real local Redis trace excerpt
The helper script `scripts/capture_trace_excerpt.py` injects a real local **Redis monitor excerpt** into this file after a local Compose run.

The script:
- attaches `redis-cli MONITOR` to the Redis service,
- triggers a few API requests,
- creates one public demo course,
- runs a one-off worker refresh to exercise Redis-backed idempotency,
- injects the captured Redis activity into the block below.

Refresh the excerpt before submission:

```bash
uv run python scripts/capture_trace_excerpt.py
```

This gives a local trace artifact that matches the EX3 expectation more closely than generic service logs.

<!-- TRACE_EXCERPT_START -->

```text
[Run `uv run python scripts/capture_trace_excerpt.py` after `docker compose up -d --build`
to replace this placeholder with a real local Redis MONITOR excerpt.]
```

<!-- TRACE_EXCERPT_END -->

## 10. CI coverage
GitHub Actions is configured in `.github/workflows/ci.yml`.

The pipeline:
1. installs Python and `uv`,
2. installs project dependencies,
3. runs Alembic migrations,
4. runs API tests,
5. runs worker tests,
6. runs Schemathesis contract tests.

This gives a reproducible CI path for both `pytest` and OpenAPI contract validation.

## 11. Submission hygiene
Before submitting, verify that the repository or ZIP does **not** include:
- `.env`
- `.venv/`
- `.pytest_cache/`
- `.hypothesis/`
- `app.db`

Also verify that all required files are committed and pushed to the GitHub repository.

## 12. External checks that cannot be proven from code alone
These items must still be verified manually because they are external to the codebase:
- AWS Academy prerequisite completion,
- whether a bonus screen capture was recorded,
- whether the correct GitHub Classroom repository and any required tags were used.

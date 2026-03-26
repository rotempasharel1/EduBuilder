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

## 9. Real local service log excerpt
The helper script `scripts/capture_trace_excerpt.py` injects a real local **service log excerpt** into this file after a Docker Compose run.

This excerpt demonstrates:
- Alembic migrations running at startup,
- the API becoming healthy,
- worker execution,
- and the background processing path that relies on Redis-backed coordination.

If your instructor specifically requires a **Logfire trace** or a **Redis trace visualization** rather than service logs, replace the block below with that capture before final submission.

<!-- TRACE_EXCERPT_START -->

```text
# worker
worker-1  |  + starlette==0.52.1
worker-1  |  + starlette-testclient==0.4.1
worker-1  |  + streamlit==1.55.0
worker-1  |  + tenacity==9.1.4
worker-1  |  + toml==0.10.2
worker-1  |  + tornado==6.5.5
worker-1  |  + typing-extensions==4.15.0
worker-1  |  + typing-inspection==0.4.2
worker-1  |  + tzdata==2025.3
worker-1  |  + urllib3==2.6.3
worker-1  |  + uvicorn==0.42.0
worker-1  |  + watchdog==6.0.0
worker-1  |  + websockets==16.0
worker-1  |  + werkzeug==3.1.6
worker-1  | INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
worker-1  | INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
worker-1  | INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
worker-1  | INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
worker-1  | [Worker] Starting background refresh worker...
worker-1  | [Worker] No public courses found. Exiting.

# api
api-1  |  + tzdata==2025.3
api-1  |  + urllib3==2.6.3
api-1  |  + uvicorn==0.42.0
api-1  |  + watchdog==6.0.0
api-1  |  + websockets==16.0
api-1  |  + werkzeug==3.1.6
api-1  | INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
api-1  | INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
api-1  | INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
api-1  | INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
api-1  | INFO:     Will watch for changes in these directories: ['/app']
api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api-1  | INFO:     Started reloader process [1] using StatReload
api-1  | INFO:     Started server process [46]
api-1  | INFO:     Waiting for application startup.
api-1  | INFO:     Application startup complete.
api-1  | INFO:     172.18.0.1:38298 - "GET /health HTTP/1.1" 200 OK
api-1  | INFO:     172.18.0.1:42052 - "GET /health HTTP/1.1" 200 OK
api-1  | INFO:     172.18.0.1:58058 - "GET /health HTTP/1.1" 200 OK
api-1  | INFO:     172.18.0.1:58058 - "GET /favicon.ico HTTP/1.1" 404 Not Found
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

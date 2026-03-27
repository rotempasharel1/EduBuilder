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

The excerpt below is a local Compose run excerpt kept in the repository as evidence of migrations, health checks, and worker execution. Refresh it with `python scripts/capture_trace_excerpt.py` before final submission if you generate a newer local run.

<!-- TRACE_EXCERPT_START -->

```text
# worker
worker-1  |  + starlette==0.52.1
worker-1  |  + streamlit==1.55.0
worker-1  | INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
worker-1  | INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
worker-1  | [Worker] Starting background refresh worker...
worker-1  | [Worker] No public courses found. Exiting.

# api
api-1  | INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
api-1  | INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api-1  | INFO:     Application startup complete.
api-1  | INFO:     172.18.0.1:38298 - "GET /health HTTP/1.1" 200 OK
```

<!-- TRACE_EXCERPT_END -->

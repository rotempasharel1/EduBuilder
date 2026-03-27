# EduBuilder

EduBuilder is a small, local-first **course builder and course catalog** developed as one continuous domain across **EX1–EX3**.

The project is intentionally scoped to run on a single laptop and to stay aligned with the course guardrail: local development, simple architecture, reproducible setup, and no cloud deployment requirement.

## Assignment mapping

### EX1 – FastAPI Foundations (Backend)
Use these files for the EX1 grading scope:
- `backend/main_ex1.py`
- `tests/test_ex1_api.py`
- `docs/EX1-notes.md`

EX1 provides a clean FastAPI backend for one core resource, `Course`, with:
- in-memory storage,
- Pydantic validation,
- CRUD endpoints,
- pytest coverage for the happy-path backend flow,
- no authentication.

### EX2 – Friendly Interface (Frontend connected to Backend)
Use these files for the EX2 grading scope:
- `frontend/app_ex2.py`
- `backend/main_ex1.py`
- `docs/EX2-notes.md`

EX2 provides a lightweight Streamlit interface that reuses the EX1 API shape:
- list existing courses immediately,
- add a new course in one screen,
- no login or security prompts,
- one small extra: visible course count and CSV export.

### EX3 – Full-Stack Microservices Final Project (KISS)
Use these files for the EX3 grading scope:
- `backend/main.py`
- `frontend/app.py`
- `scripts/refresh.py`
- `scripts/capture_trace_excerpt.py`
- `scripts/demo.sh`
- `docs/EX3-notes.md`
- `docs/runbooks/compose.md`
- `compose.yaml`
- `tests/test_api.py`
- `tests/test_worker.py`
- `tests/test_openapi.py`
- `.github/workflows/ci.yml`

EX3 provides the integrated local stack:
- SQLite persistence via SQLModel and Alembic,
- Redis-backed rate limiting and worker idempotency,
- an async worker for weekly digest generation,
- Docker Compose orchestration for API + frontend + Redis + worker,
- a security baseline with hashed passwords, JWT auth, and role checks,
- GitHub Actions CI that runs migrations, pytest, and Schemathesis contract tests.

## Main features
- **FastAPI backend** with local SQLite storage.
- **Alembic migrations** for reproducible database setup.
- **JWT authentication** for protected create, edit, delete, and draft-management flows.
- **Role-aware authorization** for admin-only routes.
- **Streamlit UI** for browsing shared courses and managing personal course content.
- **Redis rate limiting** with response headers.
- **Async worker** with bounded concurrency, retries, and Redis-backed idempotency.
- **Schemathesis contract testing** against the OpenAPI schema.

## Repository layout

```text
EduBuilder/
├─ alembic/
│  ├─ env.py
│  ├─ script.py.mako
│  └─ versions/
├─ backend/
│  ├─ __init__.py
│  ├─ auth.py
│  ├─ database.py
│  ├─ main.py
│  ├─ main_ex1.py
│  └─ models.py
├─ frontend/
│  ├─ app.py
│  └─ app_ex2.py
├─ scripts/
│  ├─ capture_trace_excerpt.py
│  ├─ demo.sh
│  ├─ migrate.py
│  ├─ refresh.py
│  └─ seed.py
├─ tests/
│  ├─ conftest.py
│  ├─ test_api.py
│  ├─ test_ex1_api.py
│  ├─ test_openapi.py
│  └─ test_worker.py
├─ docs/
│  ├─ EX1-notes.md
│  ├─ EX2-notes.md
│  ├─ EX3-notes.md
│  └─ runbooks/
│     └─ compose.md
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ compose.yaml
├─ pyproject.toml
├─ requirements.txt
├─ uv.lock
└─ README.md
```

## Core API endpoints

### Public
- `GET /health`
- `GET /courses`
- `GET /courses/shared`
- `GET /courses/{course_id}` for public courses
- `POST /auth/register`
- `POST /auth/login`

### Authenticated user
- `GET /me`
- `GET /courses/my`
- `POST /courses`
- `PUT /courses/{course_id}`
- `DELETE /courses/{course_id}`
- `POST /chat/generate_course`
- `POST /chat/draft`
- `GET /chat/draft`
- `DELETE /chat/draft`

### Admin
- `GET /admin/only`
- `GET /admin/courses`
- `DELETE /admin/courses/{course_id}`

## Prerequisites
- Python 3.11+
- `uv` for local development
- Docker Desktop or Docker Engine with Compose
- Redis is started automatically through Compose
- Optional: Gemini API key for AI generation and digest features

## Environment variables
Copy `.env.example` to `.env` for local development, but **do not commit it**.

Example:

```env
DATABASE_URL=sqlite:///./app.db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-me-for-local-dev
ADMIN_EMAIL=admin@example.com
GEMINI_API_KEY=
API_URL=http://127.0.0.1:8000
WORKER_MAX_CONCURRENCY=3
WORKER_MAX_RETRIES=3
WORKER_RETRY_DELAY_SECONDS=2
```

## Local development with uv

### 1. Create the environment
```bash
uv venv
uv sync
```

### 2. Apply database migrations
```bash
uv run python -m scripts.migrate
```

### 3. Run the backend
```bash
uv run uvicorn backend.main:app --reload
```

Backend URLs:
- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

### 4. Run the frontend in a second terminal
```bash
uv run streamlit run frontend/app.py
```

Frontend URL:
- `http://127.0.0.1:8501`

### 5. Seed sample data (optional)
```bash
uv run python scripts/seed.py
```

## EX1 quick run
```bash
uv venv
uv sync
uv run uvicorn backend.main_ex1:app --reload
uv run pytest tests/test_ex1_api.py
```

## EX2 quick run
```bash
uv venv
uv sync
uv run uvicorn backend.main_ex1:app --reload
uv run streamlit run frontend/app_ex2.py
```

## Run the full stack with Docker Compose
```bash
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- Frontend: `http://localhost:8501`
- Redis: `localhost:6379`
- Worker: background process inside the Compose stack

The API and worker both apply Alembic migrations before starting.

To stop everything:
```bash
docker compose down
```

To remove volumes and local container state:
```bash
docker compose down -v
```

## Tests

Run all tests locally:
```bash
uv run pytest
```

Run only EX1 tests:
```bash
uv run pytest tests/test_ex1_api.py
```

Run only API tests:
```bash
uv run pytest tests/test_api.py
```

Run the OpenAPI contract test:
```bash
uv run pytest tests/test_openapi.py
```

Run the worker tests:
```bash
uv run pytest tests/test_worker.py
```

## CI

GitHub Actions CI is defined in `.github/workflows/ci.yml`.

The pipeline:
1. installs Python and `uv`,
2. installs dependencies with `uv sync`,
3. applies Alembic migrations,
4. runs API tests,
5. runs worker tests,
6. runs Schemathesis contract tests.

## Demo flow for graders

A simple local demo script is included:
```bash
bash scripts/demo.sh
```

Suggested grading flow:
1. Start the stack.
2. Open `/docs` for the API and `/health` for readiness.
3. Open the Streamlit frontend.
4. Browse shared courses.
5. Register a user and create a course.
6. Verify public/shared course behavior.
7. Check admin-only route behavior.
8. Inspect Redis-backed rate limiting, worker idempotency, and the trace excerpt captured in `docs/EX3-notes.md`.

## Security baseline
- Passwords are hashed with `passlib`.
- Access is controlled with Bearer JWTs.
- Creating, editing, deleting, and draft management require authentication.
- Role checks are enforced on admin-only endpoints.
- Expired token and missing-scope scenarios are covered by tests.
- Sensitive values belong in `.env`, not in source control.

## Persistence and reproducibility
- Persistence is local SQLite through SQLModel.
- Schema setup is reproducible through **Alembic migrations**.
- Use `scripts/seed.py` for reproducible starter data.
- Do **not** commit `app.db` or any other SQLite artifacts.
- Do **not** commit `.env`, `venv/`, `.venv/`, `.pytest_cache/`, or `.hypothesis/`.

## Enhancement implemented for EX3
The chosen enhancement is a **weekly digest / recommendation summary** for courses. A background worker scans public courses, generates a short digest, and avoids repeated work through Redis-backed idempotency keys.

## Redis trace excerpt workflow
A helper script is included to refresh the checked-in **Redis trace excerpt** in `docs/EX3-notes.md` after a local Compose run:

```bash
uv run python scripts/capture_trace_excerpt.py
```

Run it after `docker compose up` so the notes file contains a real local Redis monitor excerpt showing:
- rate-limit key activity,
- request-driven Redis commands,
- worker idempotency key activity.

## AI Assistance
AI tools were used as pair-programming aids for:
- refining the FastAPI route structure,
- improving test coverage,
- tightening documentation,
- clarifying Docker Compose orchestration,
- checking the final local workflow against the assignment brief.

All AI-generated suggestions were manually reviewed, edited, and verified locally through code inspection and automated tests.

## Submission checklist
Before submission, make sure to:
- remove `.env` from the repository,
- remove `app.db` and any other SQLite artifacts from the repository,
- remove `.venv/`, `.pytest_cache/`, and `.hypothesis/` from the repository or ZIP,
- run the tests locally and verify the current output,
- run `uv run python scripts/capture_trace_excerpt.py` after the stack is up,
- confirm that `docs/EX3-notes.md` contains a **real** Redis excerpt rather than a placeholder,
- commit all required files,
- push the final branch to the correct GitHub repository.

## Important note
The following items are external to the codebase and must still be confirmed manually:
- AWS Academy prerequisite completion,
- whether a bonus screen capture was recorded,
- whether the correct GitHub Classroom repository and required tags were used.

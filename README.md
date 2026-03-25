# EduBuilder

EduBuilder is a small, local-first **course builder and course catalog** built across EX1–EX3 around one consistent domain: users can register, create courses, browse shared courses, manage public or private visibility, and use AI-assisted flows to draft course content.

The final project combines a FastAPI backend, SQLite persistence through SQLModel and Alembic, a Streamlit interface, Redis, and an async worker. Everything is designed to run locally on a single laptop.

## What this project covers

### EX1 – Backend foundation
- FastAPI service for the core `Course` resource.
- CRUD endpoints for creating, listing, updating, and deleting courses.
- Pydantic request and response models.
- Pytest coverage for authentication, protected routes, CRUD, token expiry, and scope checks.

### EX2 – Friendly interface
- Streamlit frontend that talks to the backend.
- Visitors can browse shared courses immediately.
- Signed-in users can create, edit, save, and share their own courses.
- Small extra feature: AI-assisted course drafting and course visibility management.

### EX3 – Full-stack microservices
- SQLite persistence via SQLModel with **Alembic migrations**.
- Redis-backed rate limiting and worker idempotency.
- Async worker for weekly digest generation and recommendation summaries.
- Docker Compose orchestration for API + frontend + Redis + worker.
- Security baseline with hashed passwords, JWT auth, and role/scope checks.
- GitHub Actions CI that runs migrations, pytest, and Schemathesis contract tests.

## Main features
- **FastAPI backend** with local SQLite storage.
- **Alembic migrations** for reproducible database setup.
- **JWT authentication** for creating, editing, deleting, and draft-management flows.
- **Role-aware authorization** for admin-only routes.
- **Streamlit UI** for browsing shared courses and managing personal course content.
- **Redis rate limiting** with standard response headers.
- **Async worker** with bounded concurrency, retries, and Redis-backed idempotency.
- **Schemathesis contract testing** against the OpenAPI schema.

## Repository layout

```text
EduBuilder/
├─ alembic/
│  ├─ env.py
│  ├─ script.py.mako
│  └─ versions/
│     └─ 20260317_0001_create_users_and_courses.py
├─ backend/
│  ├─ __init__.py
│  ├─ auth.py
│  ├─ database.py
│  ├─ main.py
│  └─ models.py
├─ frontend/
│  └─ app.py
├─ scripts/
│  ├─ capture_trace_excerpt.py
│  ├─ demo.sh
│  ├─ migrate.py
│  ├─ refresh.py
│  └─ seed.py
├─ tests/
│  ├─ conftest.py
│  ├─ test_api.py
│  ├─ test_openapi.py
│  └─ test_worker.py
├─ docs/
│  ├─ EX3-notes.md
│  └─ runbooks/
│     └─ compose.md
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ alembic.ini
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

Notes:
- `GEMINI_API_KEY` is optional. Without it, AI-related flows fall back to non-LLM behavior where supported.
- `JWT_SECRET_KEY` should be rotated if shared accidentally.
- Do not commit `.env`, `app.db`, or virtual environment folders.

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

This gives a concrete CI answer for “how to run Schemathesis/pytest in CI”.

## Demo flow for graders
A simple local demo script is included:

```bash
bash scripts/demo.sh
```

Suggested grading flow:
1. Start the stack.
2. Open `/docs` for the API and `/health` for readiness.
3. Open the Streamlit frontend.
4. Browse shared courses anonymously.
5. Register a user and create a private course.
6. Share that course and verify that it appears in the public catalog.
7. Check admin-only route behavior.
8. Inspect worker logs and Redis-backed processing.

## Security baseline
- Passwords are hashed with `passlib`.
- Access is controlled with Bearer JWTs.
- Creating, editing, deleting, and draft management require authentication.
- Role/scope checks are enforced on admin-only endpoints.
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

This keeps the product useful without expanding the scope into a large distributed system.

## Local service log excerpt workflow
A helper script is included to inject a real local **service log excerpt** into `docs/EX3-notes.md`:

```bash
python scripts/capture_trace_excerpt.py
```

Run it after `docker compose up` so the notes file contains a real local excerpt from your machine.

## AI assistance
AI tools were used as pair-programming aids for:
- refining the FastAPI route structure,
- improving test coverage,
- tightening documentation,
- clarifying Docker Compose orchestration,
- validating that the final local workflow matched the assignment brief.

All generated suggestions were manually reviewed, edited, and verified locally by running the application and the automated tests.

## Submission checklist
Before submission, make sure to:
- remove `.env` from the repository,
- remove `app.db` and any other SQLite artifacts from the repository,
- remove `.venv/`, `.pytest_cache/`, and `.hypothesis/` from the repository or ZIP,
- run the tests locally and verify the current output,
- run `python scripts/capture_trace_excerpt.py` after the stack is up,
- commit all required files,
- push the final branch to the correct GitHub repository.

## Important note
The following items are external to the codebase and must still be confirmed manually:
- AWS Academy prerequisite completion,
- whether a bonus screen capture was recorded,
- whether the correct GitHub Classroom repository and required tags were used.

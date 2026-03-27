# EduBuilder

EduBuilder is a small, local-first **course builder and course catalog** built across EX1–EX3 around one consistent domain.

The final project combines a FastAPI backend, SQLite persistence through SQLModel and Alembic, a Streamlit interface, Redis, and an async worker. Everything is designed to run locally on a single laptop.

## Where to find each exercise

### EX1 – Backend foundation submission
Use these files for the EX1 grading scope:
- `backend/main_ex1.py`
- `tests/test_ex1_api.py`
- `docs/EX1-notes.md`

This is the minimal FastAPI CRUD backend for the core `Course` resource:
- in-memory storage,
- Pydantic validation,
- CRUD endpoints,
- pytest coverage for the happy-path CRUD flow,
- no authentication.

### EX2 – Friendly interface submission
Use these files for the EX2 grading scope:
- `frontend/app_ex2.py`
- `docs/EX2-notes.md`

This is the lightweight Streamlit interface that reuses the EX1 backend shape:
- list existing courses immediately,
- add a new course in one screen,
- no login or security prompts in the UI,
- one small extra: visible course count and CSV export.

### EX3 – Full-stack microservices submission
Use these files for the EX3 grading scope:
- `backend/main.py`
- `frontend/app.py`
- `scripts/refresh.py`
- `scripts/capture_trace_excerpt.py`
- `docs/EX3-notes.md`
- `docs/runbooks/compose.md`
- `compose.yaml`
- `tests/test_api.py`
- `tests/test_worker.py`
- `tests/test_openapi.py`

This is the richer integrated system:
- SQLite persistence via SQLModel and Alembic,
- Redis-backed rate limiting and worker idempotency,
- async worker for weekly digest generation,
- Docker Compose orchestration for API + frontend + Redis + worker,
- security baseline with hashed passwords, JWT auth, and role checks,
- GitHub Actions CI that runs migrations, pytest, and Schemathesis contract tests.

## Quick local setup

```bash
uv venv
uv sync
```

## Run EX1

```bash
uv run uvicorn backend.main_ex1:app --reload
```

## Run EX1 tests

```bash
uv run pytest tests/test_ex1_api.py
```

## Run EX2 side-by-side
Start the EX1 API in one terminal:

```bash
uv run uvicorn backend.main_ex1:app --reload
```

Then start the Streamlit EX2 interface in a second terminal:

```bash
uv run streamlit run frontend/app_ex2.py
```

## Run EX3 stack

```bash
docker compose up --build
```

## Run the full test suite

```bash
uv run pytest
```

## Repository layout

```text
EduBuilder/
├─ alembic/
├─ backend/
│  ├─ __init__.py
│  ├─ auth.py
│  ├─ database.py
│  ├─ main.py
│  ├─ main_ex1.py
│  └─ models.py
├─ docs/
│  ├─ EX1-notes.md
│  ├─ EX2-notes.md
│  ├─ EX3-notes.md
│  └─ runbooks/
├─ frontend/
│  ├─ app.py
│  └─ app_ex2.py
├─ scripts/
├─ tests/
│  ├─ conftest.py
│  ├─ test_api.py
│  ├─ test_ex1_api.py
│  ├─ test_openapi.py
│  └─ test_worker.py
├─ compose.yaml
├─ pyproject.toml
├─ requirements.txt
└─ README.md
```

# Submission Status – EduBuilder

## EX1

Included:

- FastAPI CRUD backend
- in-memory data handling
- pytest coverage
- local README / notes

Main grading files:

- `poseai_backend/main_ex1.py`
- `tests/test_ex1_api.py`
- `docs/EX1-notes.md`

## EX2

Included:

- Streamlit frontend
- reuse of the EX1 API
- quick list/create flow
- one small extra for usability

Main grading files:

- `frontend/app_ex2.py`
- `poseai_backend/main_ex1.py`
- `docs/EX2-notes.md`

## EX3

Included:

- FastAPI backend
- SQLite / SQLModel persistence
- Alembic migrations
- Streamlit frontend
- Redis-backed rate limiting
- async worker with retries, bounded concurrency, and idempotency
- JWT auth and role checks
- automated tests
- Docker Compose runbook
- local demo script

Main grading files:

- `poseai_backend/main.py`
- `poseai_backend/auth.py`
- `poseai_backend/database.py`
- `poseai_backend/models.py`
- `frontend/app.py`
- `scripts/refresh.py`
- `scripts/migrate.py`
- `scripts/seed.py`
- `scripts/demo.sh`
- `scripts/capture_trace_excerpt.py`
- `compose.yaml`
- `docs/EX3-notes.md`
- `docs/runbooks/compose.md`
- `tests/test_api.py`
- `tests/test_worker.py`
- `tests/test_openapi.py`
- `.github/workflows/ci.yml`

## Final note

Before the final push, make sure the trace excerpt section in `docs/EX3-notes.md` contains a real local excerpt captured from your machine.

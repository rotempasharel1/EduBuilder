# EX1 Notes – EduBuilder Backend

This file presents **EX1 separately** from the richer EX3 system.

## Goal
Show a clean FastAPI backend for one core resource: `Course`.

## Files used for EX1
- `backend/main_ex1.py`
- `tests/test_ex1_api.py`
- `docs/EX1-notes.md`

## Local setup
```bash
uv venv
uv sync
```

## Run the API
```bash
uv run uvicorn backend.main_ex1:app --reload
```

## What this version includes
- FastAPI backend
- one core resource: `Course`
- CRUD endpoints:
  - `GET /courses`
  - `GET /courses/{course_id}`
  - `POST /courses`
  - `PUT /courses/{course_id}`
  - `DELETE /courses/{course_id}`
- health endpoint: `GET /health`
- no authentication
- simple in-memory data store
- pytest coverage for listing and create/update/delete happy-path flows

## Tests
```bash
uv run pytest tests/test_ex1_api.py
```

## Notes on scope
The full repository later evolved into EX3 and includes authentication, SQLite persistence, Redis, worker flows, and AI features.

For the EX1 grading scope, `backend/main_ex1.py` keeps the implementation small and focused on the backend foundations required by the assignment.

## AI Assistance
AI tools were used to:
- review route naming and response consistency,
- tighten the README and notes wording,
- sanity-check the CRUD test coverage.

All suggested changes were manually reviewed and verified locally through code inspection and pytest.

# EX1 Notes – PoseAI Trainer Backend

This file presents **EX1 separately** from the richer EX3 system.

## Goal
Show a clean FastAPI backend for one core resource: `Plan`.

## Files used for EX1
- `poseai_backend/main_ex1.py`
- `tests/test_ex1_api.py`

## Local setup
```bash
uv venv
uv pip install -r requirements.txt
```

## Run the API
```bash
uv run uvicorn poseai_backend.main_ex1:app --reload
```

## What this version includes
- FastAPI backend
- one core resource: `Plan`
- CRUD endpoints:
  - `GET /plans`
  - `GET /plans/{plan_id}`
  - `POST /plans`
  - `PUT /plans/{plan_id}`
  - `DELETE /plans/{plan_id}`
- health endpoint: `GET /health`
- no authentication
- simple in-memory data store
- pytest coverage for the happy-path CRUD flow

## Tests
```bash
uv run pytest tests/test_ex1_api.py
```

## AI Assistance
AI tools were used to help draft the file structure and test outline. All code should be reviewed locally and verified by running the API and pytest before submission.

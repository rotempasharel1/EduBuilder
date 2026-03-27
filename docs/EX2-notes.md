# EX2 Notes – EduBuilder Frontend

This file presents **EX2 separately** from the richer EX3 interface.

## Goal
Show a lightweight Streamlit interface connected to the EduBuilder API.

## Files used for EX2
- `frontend/app_ex2.py`
- `backend/main_ex1.py` for the cleanest EX2 demo
- `docs/EX2-notes.md`

## Local setup
```bash
uv venv
uv sync
```

## Recommended EX2 run
Run the API first, then launch the EX2 interface:

```bash
uv run uvicorn backend.main_ex1:app --reload
uv run streamlit run frontend/app_ex2.py
```

## What this version includes
- lists existing courses immediately,
- allows adding a new course in one screen,
- no login or security prompts,
- one small extra:
  - visible course count,
  - CSV export of the current catalog.

## Expected local URLs
- API: `http://127.0.0.1:8000`
- Streamlit: `http://127.0.0.1:8501`

## Notes on scope
The main EX3 frontend is richer and includes sign-in, private courses, admin features, and AI-assisted flows.

For the EX2 grading scope, `frontend/app_ex2.py` keeps the interface focused and fast to demonstrate in under a minute from launch.

## AI Assistance
AI tools were used to:
- improve the wording and structure of the user-facing copy,
- review the Streamlit layout for a faster demo flow,
- check that the extra feature stayed small and in scope.

All suggestions were manually reviewed and verified locally against the running API.

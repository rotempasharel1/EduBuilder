# EX2 Notes – PoseAI Trainer Frontend

This file presents **EX2 separately** from the richer EX3 interface.

## Goal
Show a lightweight Streamlit interface connected to the EX1 API.

## Files used for EX2
- `frontend/app_ex2.py`
- `poseai_backend/main_ex1.py`
- `docs/EX2-notes.md`

## Local setup
```bash
uv venv
uv pip install -r requirements.txt
```

## Recommended EX2 run
Run the API first, then launch the EX2 interface:

```bash
uv run uvicorn poseai_backend.main_ex1:app --reload
uv run streamlit run frontend/app_ex2.py
```

## What this version includes
- lists existing plans immediately
- allows adding a new plan in one screen
- no login or security prompts in the UI
- one small extra:
  - visible plan count
  - CSV export of the current catalog

## Expected local URLs
- API: `http://127.0.0.1:8000`
- Streamlit: `http://127.0.0.1:8501`

## AI Assistance
AI tools were used to help draft the Streamlit skeleton and simplify the UI wording. All flows should be verified locally against the running backend before submission.

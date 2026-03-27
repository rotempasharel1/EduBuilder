from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="PoseAI Trainer EX1 API", version="1.0.0")


class PlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=240)
    cues: str = Field(min_length=1)
    level: str = Field(min_length=1, max_length=40)
    is_public: bool = True


class PlanUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=240)
    cues: str = Field(min_length=1)
    level: str = Field(min_length=1, max_length=40)
    is_public: bool = True


class Plan(BaseModel):
    id: int
    title: str
    goal: str
    cues: str
    level: str
    is_public: bool = True
    created_at: str


PLANS: Dict[int, Plan] = {}
_NEXT_ID = count(1)


def _new_plan_id() -> int:
    return next(_NEXT_ID)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/plans", response_model=list[Plan])
def list_plans() -> list[Plan]:
    return list(PLANS.values())


@app.get("/plans/{plan_id}", response_model=Plan)
def get_plan(plan_id: int) -> Plan:
    plan = PLANS.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.post("/plans", response_model=Plan)
def create_plan(payload: PlanCreate) -> Plan:
    plan = Plan(
        id=_new_plan_id(),
        title=payload.title,
        goal=payload.goal,
        cues=payload.cues,
        level=payload.level,
        is_public=payload.is_public,
        created_at=_now_iso(),
    )
    PLANS[plan.id] = plan
    return plan


@app.put("/plans/{plan_id}", response_model=Plan)
def update_plan(plan_id: int, payload: PlanUpdate) -> Plan:
    existing = PLANS.get(plan_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    updated = existing.model_copy(
        update={
            "title": payload.title,
            "goal": payload.goal,
            "cues": payload.cues,
            "level": payload.level,
            "is_public": payload.is_public,
        }
    )
    PLANS[plan_id] = updated
    return updated


@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: int) -> dict[str, str]:
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    del PLANS[plan_id]
    return {"status": "success"}

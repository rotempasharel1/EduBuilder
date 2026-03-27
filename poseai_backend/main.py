from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from redis.asyncio import Redis
from sqlmodel import Session, select
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_access_token,
    get_password_hash,
    optional_security,
    required_security,
    verify_password,
)
from .database import get_session, init_db
from .models import EmailLoginRequest, EmailRegisterRequest, Plan, PlanCreate, PlanRead, User


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.redis = Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    yield
    close_method = getattr(app.state.redis, "aclose", None) or getattr(app.state.redis, "close", None)
    if close_method is not None:
        result = close_method()
        if hasattr(result, "__await__"):
            await result


app = FastAPI(title="PoseAI Trainer API", lifespan=lifespan)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_host}"
        limit = 60
        window = 60

        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window)

            remaining = max(limit - count, 0)
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"},
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        except Exception:
            return await call_next(request)


app.add_middleware(RateLimitMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


def get_current_user(
    security_scopes: SecurityScopes,
    token: HTTPAuthorizationCredentials = Depends(required_security),
    session: Session = Depends(get_session),
) -> User:
    payload = decode_access_token(token.credentials)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_scopes = payload.get("scopes", [])
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")

    return user


def get_optional_user(
    token: HTTPAuthorizationCredentials | None = Depends(optional_security),
    session: Session = Depends(get_session),
) -> Optional[User]:
    if token is None:
        return None

    try:
        payload = decode_access_token(token.credentials)
    except HTTPException:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return session.get(User, user_id)


def require_admin(user: User = Security(get_current_user, scopes=["admin"])):
    return user


def build_token_for_user(user: User) -> str:
    scopes = ["read", "write"]
    if user.role == "admin":
        scopes.append("admin")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": user.id, "scopes": scopes},
        expires_delta=access_token_expires,
    )


def enrich_plans_with_owner(plans: list[Plan], session: Session) -> list[dict]:
    enriched: list[dict] = []
    for plan in plans:
        owner = session.get(User, plan.owner_id)
        item = PlanRead(
            id=plan.id,
            owner_id=plan.owner_id,
            title=plan.title,
            goal=plan.goal,
            cues=plan.cues,
            level=plan.level,
            is_public=plan.is_public,
            weekly_digest=plan.weekly_digest,
            created_at=plan.created_at,
            owner_name=owner.full_name if owner else "Unknown",
            owner_email=owner.email if owner else "Unknown",
        )
        enriched.append(item.model_dump())
    return enriched


@app.post("/auth/register")
def register(user_data: EmailRegisterRequest, session: Session = Depends(get_session)):
    email = user_data.email.strip().lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role="admin" if email == os.environ.get("ADMIN_EMAIL", "admin@example.com") else "user",
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    access_token = build_token_for_user(new_user)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/login")
def login(user_data: EmailLoginRequest, session: Session = Depends(get_session)):
    email = user_data.email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = build_token_for_user(user)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/admin/only")
def admin_only(user: User = Security(get_current_user, scopes=["admin"])):
    return {"status": "admin_verified", "email": user.email}


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


@app.get("/plans")
def list_plans(
    session: Session = Depends(get_session),
    mine: bool = False,
    user: User | None = Depends(get_optional_user),
):
    stmt = select(Plan)

    if mine:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required for mine=true")
        stmt = stmt.where(Plan.owner_id == user.id)
    else:
        stmt = stmt.where(Plan.is_public.is_(True))

    plans = session.exec(stmt.order_by(Plan.created_at.desc())).all()
    return enrich_plans_with_owner(plans, session)


@app.get("/plans/shared")
def get_shared_plans(session: Session = Depends(get_session)):
    plans = session.exec(
        select(Plan)
        .where(Plan.is_public.is_(True))
        .order_by(Plan.created_at.desc())
    ).all()
    return enrich_plans_with_owner(plans, session)


@app.get("/plans/my")
def get_my_plans(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    plans = session.exec(
        select(Plan)
        .where(Plan.owner_id == user.id)
        .order_by(Plan.created_at.desc())
    ).all()
    return enrich_plans_with_owner(plans, session)


@app.get("/plans/{plan_id}")
def get_plan(
    plan_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(get_optional_user),
):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan.is_public:
        if user is None or (user.id != plan.owner_id and user.role != "admin"):
            raise HTTPException(status_code=403, detail="Plan is private")

    enriched = enrich_plans_with_owner([plan], session)
    return enriched[0]


@app.post("/plans")
def create_plan(
    payload: PlanCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    new_plan = Plan(
        owner_id=user.id,
        title=payload.title,
        goal=payload.goal,
        cues=payload.cues,
        level=payload.level,
        is_public=payload.is_public,
    )
    session.add(new_plan)
    session.commit()
    session.refresh(new_plan)
    return new_plan


@app.put("/plans/{plan_id}")
def update_plan(
    plan_id: str,
    payload: PlanCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.get(Plan, plan_id)
    if not existing or existing.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Plan not found or no permission")

    existing.title = payload.title
    existing.goal = payload.goal
    existing.cues = payload.cues
    existing.level = payload.level
    existing.is_public = payload.is_public
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


@app.delete("/plans/{plan_id}")
def delete_my_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.get(Plan, plan_id)
    if not existing or existing.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Plan not found or no permission")

    session.delete(existing)
    session.commit()
    return {"status": "success"}


@app.get("/admin/plans")
def get_all_plans(
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    plans = session.exec(select(Plan).order_by(Plan.created_at.desc())).all()
    return enrich_plans_with_owner(plans, session)


@app.delete("/admin/plans/{plan_id}")
def delete_plan_as_admin(
    plan_id: str,
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    existing = session.get(Plan, plan_id)
    if existing:
        session.delete(existing)
        session.commit()
    return {"status": "success"}

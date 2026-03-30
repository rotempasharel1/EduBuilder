from __future__ import annotations

import json
import os
import re
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from pydantic import BaseModel, Field
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
    app.state.local_drafts: dict[str, dict[str, Any]] = {}
    yield
    close_method = getattr(app.state.redis, "aclose", None) or getattr(app.state.redis, "close", None)
    if close_method is not None:
        result = close_method()
        if hasattr(result, "__await__"):
            await result


app = FastAPI(title="EduBuilder API", lifespan=lifespan)


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


class CoursePayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_public: bool = False


class ChatGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    context: str = ""


class ChatDraftPayload(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    course_pages: list[dict[str, Any]] = Field(default_factory=list)
    current_page_index: int = 0
    last_saved_course_id: Optional[str] = None
    course_is_public: bool = False


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


def enrich_plans_with_owner(plans: list[Plan], session: Session) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
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


def plan_to_course(plan: Plan, session: Session) -> dict[str, Any]:
    owner = session.get(User, plan.owner_id)
    return {
        "id": plan.id,
        "owner_id": plan.owner_id,
        "owner_name": owner.full_name if owner else "Unknown",
        "owner_email": owner.email if owner else "Unknown",
        "title": plan.title,
        "content": plan.goal,
        "is_public": plan.is_public,
        "weekly_digest": plan.weekly_digest,
        "created_at": plan.created_at,
    }


def plans_to_courses(plans: list[Plan], session: Session) -> list[dict[str, Any]]:
    return [plan_to_course(plan, session) for plan in plans]


def infer_course_title(content: str) -> str:
    first_heading = re.search(r"^###\\s+(.+)$", content, flags=re.MULTILINE)
    if first_heading:
        return first_heading.group(1).strip()[:200]
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "My Course")
    return first_line[:200]


def infer_topic(prompt: str) -> str:
    text = prompt.strip()
    lowered = text.lower()

    patterns = [
        r"create (?:an?|the)?\\s*(.+?)\\s+course(?: for me)?$",
        r"build (?:an?|the)?\\s*(.+?)\\s+course(?: for me)?$",
        r"make (?:an?|the)?\\s*(.+?)\\s+course(?: for me)?$",
        r"(?:an?|the)?\\s*(.+?)\\s+course$",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            topic = match.group(1).strip(" .")
            if topic:
                return topic.title()

    return text.strip().rstrip(".")[:80].title() or "General Learning"


def existing_content_page_count(context: str) -> int:
    count = 0
    for line in context.splitlines():
        if line.strip().startswith("### "):
            count += 1
    return count


def build_page(topic: str, chapter_number: int) -> dict[str, str]:
    if chapter_number == 1:
        title = f"{topic}: Foundations"
        content = (
            f"Welcome to **{topic}**.\\n\\n"
            "In this opening chapter we build the basic vocabulary, the central questions in the field, "
            "and the reason the topic matters in real life.\\n\\n"
            "Key ideas:\\n"
            "- Define the subject clearly\\n"
            "- Identify the main goals of the field\\n"
            "- Connect theory to daily examples"
        )
    elif chapter_number == 2:
        title = f"{topic}: Core Concepts"
        content = (
            f"This chapter introduces the main concepts in **{topic}** and explains how they connect.\\n\\n"
            "Focus points:\\n"
            "- Core models and definitions\\n"
            "- Typical examples learners should recognize\\n"
            "- Common misunderstandings and how to avoid them"
        )
    elif chapter_number == 3:
        title = f"{topic}: Applications and Practice"
        content = (
            f"Now we move from theory into practice in **{topic}**.\\n\\n"
            "In this chapter learners should:\\n"
            "- Apply concepts to realistic scenarios\\n"
            "- Compare different approaches\\n"
            "- Explain their reasoning in simple language"
        )
    else:
        title = f"{topic}: Chapter {chapter_number}"
        content = (
            f"This chapter expands the learner's understanding of **{topic}** with a new angle.\\n\\n"
            "Suggested structure:\\n"
            "- Short concept recap\\n"
            "- One deeper example\\n"
            "- Reflection question or mini exercise"
        )
    return {"title": title, "content": content}


def build_quiz(topic: str, chapter_number: int) -> list[dict[str, Any]]:
    return [
        {
            "question": f"What is the main goal of studying {topic} in this chapter?",
            "options": [
                "To memorize unrelated facts only",
                "To understand central ideas and apply them",
                "To avoid examples completely",
                "To focus only on advanced research terminology",
            ],
            "correct_answer": "To understand central ideas and apply them",
            "explanation": "A strong introduction should help the learner understand the main ideas and use them in context.",
        },
        {
            "question": f"Which learning activity best supports progress in {topic}?",
            "options": [
                "Connecting concepts to examples",
                "Ignoring definitions",
                "Skipping all review",
                "Reading headings only",
            ],
            "correct_answer": "Connecting concepts to examples",
            "explanation": "Examples make abstract ideas clearer and easier to remember.",
        },
        {
            "question": f"What should a learner be able to do after chapter {chapter_number}?",
            "options": [
                "Recall and explain the key ideas",
                "Master every advanced specialization",
                "Avoid asking questions",
                "Ignore practice tasks",
            ],
            "correct_answer": "Recall and explain the key ideas",
            "explanation": "The immediate goal is understanding and explanation, not total mastery of every advanced topic.",
        },
    ]


async def load_draft_for_user(user_id: str) -> dict[str, Any]:
    redis = getattr(app.state, "redis", None)
    if redis is not None:
        try:
            raw = await redis.get(f"chat_draft:{user_id}")
            if raw:
                return json.loads(raw)
        except Exception:
            pass

    return app.state.local_drafts.get(user_id, {})


async def save_draft_for_user(user_id: str, draft: dict[str, Any]) -> None:
    app.state.local_drafts[user_id] = draft

    redis = getattr(app.state, "redis", None)
    if redis is not None:
        try:
            await redis.set(f"chat_draft:{user_id}", json.dumps(draft))
        except Exception:
            pass


async def delete_draft_for_user(user_id: str) -> None:
    app.state.local_drafts.pop(user_id, None)

    redis = getattr(app.state, "redis", None)
    if redis is not None:
        try:
            await redis.delete(f"chat_draft:{user_id}")
        except Exception:
            pass


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


@app.post("/chat/generate_course")
def generate_course(
    payload: ChatGenerateRequest,
    user: User = Depends(get_current_user),
):
    topic = infer_topic(payload.prompt)
    current_pages = existing_content_page_count(payload.context)

    lowered = payload.prompt.lower()
    wants_continue = any(
        phrase in lowered
        for phrase in [
            "continue",
            "next chapter",
            "another chapter",
            "add chapter",
            "keep building",
        ]
    )

    if wants_continue and current_pages > 0:
        next_page = build_page(topic, current_pages + 1)
        pages = [next_page]
        quiz = build_quiz(topic, current_pages + 1) if (current_pages + 1) % 2 == 0 else []
        chat_message = f"I added the next chapter for **{topic}**."
    else:
        pages = [
            build_page(topic, 1),
            build_page(topic, 2),
            build_page(topic, 3),
        ]
        quiz = build_quiz(topic, 3)
        chat_message = f"I created a starter course for **{topic}** with three lesson pages and a short quiz."

    return {
        "chat_message": chat_message,
        "pages": pages,
        "quiz": quiz,
    }


@app.get("/chat/draft")
async def get_chat_draft(user: User = Depends(get_current_user)):
    return await load_draft_for_user(user.id)


@app.post("/chat/draft")
async def save_chat_draft(
    payload: ChatDraftPayload,
    user: User = Depends(get_current_user),
):
    draft = payload.model_dump()
    await save_draft_for_user(user.id, draft)
    return {"status": "saved"}


@app.delete("/chat/draft")
async def delete_chat_draft(user: User = Depends(get_current_user)):
    await delete_draft_for_user(user.id)
    return {"status": "deleted"}


@app.get("/courses/shared")
def get_shared_courses(session: Session = Depends(get_session)):
    plans = session.exec(
        select(Plan)
        .where(Plan.is_public.is_(True))
        .order_by(Plan.created_at.desc())
    ).all()
    return plans_to_courses(plans, session)


@app.get("/courses/my")
def get_my_courses(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    plans = session.exec(
        select(Plan)
        .where(Plan.owner_id == user.id)
        .order_by(Plan.created_at.desc())
    ).all()
    return plans_to_courses(plans, session)


@app.post("/courses")
def create_course(
    payload: CoursePayload,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    title = payload.title.strip() or infer_course_title(payload.content)
    new_plan = Plan(
        owner_id=user.id,
        title=title,
        goal=payload.content,
        cues="EduBuilder generated course content",
        level="General",
        is_public=payload.is_public,
    )
    session.add(new_plan)
    session.commit()
    session.refresh(new_plan)
    return plan_to_course(new_plan, session)


@app.put("/courses/{course_id}")
def update_course(
    course_id: str,
    payload: CoursePayload,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.get(Plan, course_id)
    if not existing or existing.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found or no permission")

    existing.title = payload.title.strip() or infer_course_title(payload.content)
    existing.goal = payload.content
    existing.is_public = payload.is_public
    if not existing.cues:
        existing.cues = "EduBuilder generated course content"
    if not existing.level:
        existing.level = "General"

    session.add(existing)
    session.commit()
    session.refresh(existing)
    return plan_to_course(existing, session)


@app.delete("/courses/{course_id}")
def delete_course(
    course_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.get(Plan, course_id)
    if not existing or existing.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found or no permission")

    session.delete(existing)
    session.commit()
    return {"status": "success"}


@app.get("/admin/courses")
def get_all_courses(
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    plans = session.exec(select(Plan).order_by(Plan.created_at.desc())).all()
    return plans_to_courses(plans, session)


@app.delete("/admin/courses/{course_id}")
def delete_course_as_admin(
    course_id: str,
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    existing = session.get(Plan, course_id)
    if existing:
        session.delete(existing)
        session.commit()
    return {"status": "success"}


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

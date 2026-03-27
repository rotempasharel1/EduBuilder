import json
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from google import genai
from google.genai import types
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
from .models import (
    ChatRequest,
    Course,
    CourseCreate,
    CourseGenerationResponse,
    CourseRead,
    DraftState,
    EmailLoginRequest,
    EmailRegisterRequest,
    User,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.redis = Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(title="EduBuilder Course Builder API", lifespan=lifespan)


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


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


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


def enrich_courses_with_owner(courses: list[Course], session: Session) -> list[dict]:
    enriched: list[dict] = []
    for course in courses:
        owner = session.get(User, course.owner_id)
        item = CourseRead(
            id=course.id,
            owner_id=course.owner_id,
            title=course.title,
            content=course.content,
            is_public=course.is_public,
            weekly_digest=course.weekly_digest,
            created_at=course.created_at,
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


@app.post("/chat/generate_course")
def generate_course(payload: ChatRequest, user: User = Depends(get_current_user)):
    if not genai_client:
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured on this server. AI features are disabled.",
        )

    prompt = payload.prompt.strip()
    context = (payload.context or "").strip()

    try:
        system_instructions = (
            "You are an expert AI teacher that builds educational courses chapter by chapter. "
            "Generate exactly 5 pages, then exactly 5 multiple-choice questions, then a short "
            "follow-up message. All output must be in English and valid JSON matching the provided schema."
        )

        full_prompt = f"Context/Previous Lesson context: {context}\n\nUser Prompt: {prompt}"

        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instructions,
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=16384,
                response_mime_type="application/json",
                response_schema=CourseGenerationResponse,
            ),
        )

        if not response.text:
            raise HTTPException(status_code=500, detail="Gemini returned an empty response.")

        return json.loads(response.text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini error: {exc}")


@app.post("/chat/draft")
def save_chat_draft(
    draft: DraftState,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        draft_content = draft.model_dump_json()
        existing = session.exec(
            select(Course).where(
                Course.owner_id == user.id,
                Course.title == "__DRAFT_STATE__",
            )
        ).first()

        if existing:
            existing.content = draft_content
            session.add(existing)
        else:
            session.add(
                Course(
                    owner_id=user.id,
                    title="__DRAFT_STATE__",
                    content=draft_content,
                    is_public=False,
                )
            )

        session.commit()
        return {"status": "ok"}
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/chat/draft")
def load_chat_draft(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        existing = session.exec(
            select(Course).where(
                Course.owner_id == user.id,
                Course.title == "__DRAFT_STATE__",
            )
        ).first()
        if existing:
            return json.loads(existing.content)
        return None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/chat/draft")
def delete_chat_draft(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        existing = session.exec(
            select(Course).where(
                Course.owner_id == user.id,
                Course.title == "__DRAFT_STATE__",
            )
        ).first()
        if existing:
            session.delete(existing)
            session.commit()
        return {"status": "ok"}
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/courses")
def list_courses(
    session: Session = Depends(get_session),
    mine: bool = False,
    user: User | None = Depends(get_optional_user),
):
    try:
        stmt = select(Course).where(Course.title != "__DRAFT_STATE__")

        if mine:
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required for mine=true")
            stmt = stmt.where(Course.owner_id == user.id)
        else:
            stmt = stmt.where(Course.is_public.is_(True))

        courses = session.exec(stmt.order_by(Course.created_at.desc())).all()
        return enrich_courses_with_owner(courses, session)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/courses/shared")
def get_shared_courses(session: Session = Depends(get_session)):
    try:
        courses = session.exec(
            select(Course)
            .where(Course.is_public.is_(True), Course.title != "__DRAFT_STATE__")
            .order_by(Course.created_at.desc())
        ).all()
        return enrich_courses_with_owner(courses, session)
    except Exception:
        return []


@app.get("/courses/my")
def get_my_courses(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        courses = session.exec(
            select(Course)
            .where(Course.owner_id == user.id, Course.title != "__DRAFT_STATE__")
            .order_by(Course.created_at.desc())
        ).all()
        return enrich_courses_with_owner(courses, session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/courses/{course_id}")
def get_course(
    course_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(get_optional_user),
):
    try:
        course = session.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if not course.is_public:
            if user is None or (user.id != course.owner_id and user.role != "admin"):
                raise HTTPException(status_code=403, detail="Course is private")

        enriched = enrich_courses_with_owner([course], session)
        return enriched[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/courses")
def save_course(
    project: CourseCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        new_course = Course(
            owner_id=user.id,
            title=project.title,
            content=project.content,
            is_public=project.is_public,
        )
        session.add(new_course)
        session.commit()
        session.refresh(new_course)
        return new_course
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/courses/{course_id}")
def update_course(
    course_id: str,
    project: CourseCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        existing = session.get(Course, course_id)
        if not existing or existing.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Course not found or no permission.")

        existing.title = project.title
        existing.content = project.content
        existing.is_public = project.is_public
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/admin/courses")
def get_all_courses(
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    try:
        courses = session.exec(
            select(Course)
            .where(Course.title != "__DRAFT_STATE__")
            .order_by(Course.created_at.desc())
        ).all()
        return enrich_courses_with_owner(courses, session)
    except Exception:
        return []


@app.delete("/admin/courses/{course_id}")
def delete_course(
    course_id: str,
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    try:
        existing = session.get(Course, course_id)
        if existing:
            session.delete(existing)
            session.commit()
        return {"status": "success"}
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/courses/{course_id}")
def delete_my_course(
    course_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        existing = session.get(Course, course_id)
        if not existing or existing.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Course not found or no permission.")

        session.delete(existing)
        session.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

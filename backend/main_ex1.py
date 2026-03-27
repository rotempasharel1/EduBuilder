from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="EduBuilder EX1 API", version="1.0.0")


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_public: bool = True


class CourseUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_public: bool = True


class Course(BaseModel):
    id: int
    title: str
    content: str
    is_public: bool = True
    created_at: str


COURSES: Dict[int, Course] = {}
_NEXT_ID = count(1)


def _new_course_id() -> int:
    return next(_NEXT_ID)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/courses", response_model=list[Course])
def list_courses() -> list[Course]:
    return list(COURSES.values())


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: int) -> Course:
    course = COURSES.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.post("/courses", response_model=Course)
def create_course(payload: CourseCreate) -> Course:
    course = Course(
        id=_new_course_id(),
        title=payload.title,
        content=payload.content,
        is_public=payload.is_public,
        created_at=_now_iso(),
    )
    COURSES[course.id] = course
    return course


@app.put("/courses/{course_id}", response_model=Course)
def update_course(course_id: int, payload: CourseUpdate) -> Course:
    existing = COURSES.get(course_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Course not found")

    updated = existing.model_copy(
        update={
            "title": payload.title,
            "content": payload.content,
            "is_public": payload.is_public,
        }
    )
    COURSES[course_id] = updated
    return updated


@app.delete("/courses/{course_id}")
def delete_course(course_id: int) -> dict[str, str]:
    if course_id not in COURSES:
        raise HTTPException(status_code=404, detail="Course not found")
    del COURSES[course_id]
    return {"status": "success"}

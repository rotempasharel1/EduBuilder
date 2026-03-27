from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, Field as PydanticField
from sqlmodel import Field, SQLModel


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    role: str = Field(default="user")
    created_at: datetime = Field(default_factory=utc_now)


class Plan(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    title: str
    goal: str
    cues: str
    level: str
    is_public: bool = Field(default=False)
    weekly_digest: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class PlanCreate(BaseModel):
    title: str = PydanticField(min_length=1, max_length=120)
    goal: str = PydanticField(min_length=1, max_length=240)
    cues: str = PydanticField(min_length=1)
    level: str = PydanticField(min_length=1, max_length=40)
    is_public: bool = False


class PlanRead(BaseModel):
    id: str
    owner_id: str
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    title: str
    goal: str
    cues: str
    level: str
    is_public: bool
    weekly_digest: Optional[str] = None
    created_at: datetime


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str = PydanticField(min_length=8)


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str = PydanticField(min_length=8)
    full_name: str = PydanticField(min_length=2, max_length=100)

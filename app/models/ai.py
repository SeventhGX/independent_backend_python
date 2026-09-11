import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatBody(BaseModel):
    id: uuid.UUID | None = None
    session_name: str | None = None
    model_type: str | None = None
    model: str | None = None
    content: dict | None = None
    create_time: datetime | None = None


class ChatBodyV2(BaseModel):
    id: uuid.UUID | None = None
    session_name: str | None = None
    model_type: str
    model: str
    content: dict | None = None
    kwargs: dict | None = None
    create_time: datetime | None = None


class SessionShareOrigin(BaseModel):
    share_code: str
    shared_by: str | None = None
    origin_session_id: uuid.UUID | None = None


class SessionSummaryResponse(BaseModel):
    id: uuid.UUID
    session_name: str | None = None
    create_time: datetime | None = None
    shared_from: SessionShareOrigin | None = None
    is_shared_by_me: bool = False


class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    session_name: str | None = None
    create_time: datetime | None = None
    content: dict | None = None
    shared_from: SessionShareOrigin | None = None
    is_shared_by_me: bool = False


class CreateSessionShareRequest(BaseModel):
    session_id: uuid.UUID
    expire_days: int | None = Field(default=None, ge=1, le=365)


class SessionShareResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    session_name: str | None = None
    share_code: str
    create_time: datetime | None = None
    expire_time: datetime | None = None
    visit_count: int = 0
    is_expired: bool = False


class SharedSessionResponse(BaseModel):
    share_code: str
    session_id: uuid.UUID
    session_name: str | None = None
    content: dict | None = None
    create_time: datetime | None = None
    expire_time: datetime | None = None
    shared_by: str | None = None
    is_owner: bool = False


class SaveSharedSessionRequest(BaseModel):
    share_code: str = Field(min_length=1, max_length=64)
    session_name: str | None = Field(default=None, max_length=200)

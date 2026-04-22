from datetime import datetime
from pydantic import BaseModel
import uuid


class ChatBody(BaseModel):
    id: uuid.UUID | None = None
    session_name: str | None = None
    model_type: str | None = None
    model: str | None = None
    content: dict | None = None
    create_time: datetime | None = None

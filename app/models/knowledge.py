from pydantic import BaseModel
import uuid


class KnowledgeResponse(BaseModel):
    file_id: uuid.UUID
    knowledge_id: uuid.UUID
    filename: str | None
    file_type: str | None
    is_embedded: bool

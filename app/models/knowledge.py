from pydantic import BaseModel
from datetime import datetime
import uuid


class KnowledgeResponse(BaseModel):
    file_id: uuid.UUID
    knowledge_id: uuid.UUID
    filename: str | None
    file_type: str | None
    is_embedded: bool
    create_time: datetime | None


class DeleteKnowledgeFilesRequest(BaseModel):
    file_ids: list[uuid.UUID]


class DeleteKnowledgeFilesResponse(BaseModel):
    deleted_file_ids: list[uuid.UUID]
    deleted_count: int


class RagRetrieveRequest(BaseModel):
    query: str
    file_ids: list[uuid.UUID] | None = None
    top_k: int = 10


class RagChunkResponse(BaseModel):
    chunk_id: uuid.UUID
    file_id: uuid.UUID
    chunk_index: int
    content: str
    meta_data: dict | None = None
    score: float


class RagChatRequest(RagRetrieveRequest):
    # model: str = "deepseek-v4-pro"
    temperature: float = 0.2


class RagChatResponse(BaseModel):
    answer: str
    chunks: list[RagChunkResponse]

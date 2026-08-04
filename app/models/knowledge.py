import uuid
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


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


class RetrievalMethod(StrEnum):
    VECTOR = "vector"
    HYBRID = "hybrid"


class RagRetrieveRequest(BaseModel):
    query: str
    file_ids: list[uuid.UUID] | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR
    semantic_weight: float = Field(default=0.7, ge=0, le=1)
    keyword_weight: float = Field(default=0.3, ge=0, le=1)

    @model_validator(mode="after")
    def validate_hybrid_weights(self) -> Self:
        if abs(self.semantic_weight + self.keyword_weight - 1) > 1e-6:
            raise ValueError("semantic_weight 与 keyword_weight 之和必须为 1")
        return self


class RagChunkResponse(BaseModel):
    chunk_id: uuid.UUID
    file_id: uuid.UUID
    chunk_index: int
    content: str
    meta_data: dict | None = None
    score: float
    semantic_score: float
    keyword_score: float | None = None
    retrieval_method: RetrievalMethod


class RagChatRequest(RagRetrieveRequest):
    # model: str = "deepseek-v4-pro"
    temperature: float = 0.2


class RagChatResponse(BaseModel):
    answer: str
    chunks: list[RagChunkResponse]

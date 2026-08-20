import uuid
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

PUBLIC_KNOWLEDGE_SOURCE_PREFIX = "knowledge-public://"


class KnowledgeTagResponse(BaseModel):
    id: uuid.UUID
    name: str


class KnowledgeTagsResponse(BaseModel):
    file_id: uuid.UUID
    tags: list[KnowledgeTagResponse]


class KnowledgeResponse(BaseModel):
    file_id: uuid.UUID
    knowledge_id: uuid.UUID
    filename: str | None
    file_type: str | None
    is_embedded: bool
    create_time: datetime | None
    source: str
    is_public: bool = False
    tags: list[KnowledgeTagResponse] = Field(default_factory=list)


class KnowledgeFileIdsRequest(BaseModel):
    file_ids: list[uuid.UUID] = Field(min_length=1)


class KnowledgeVisibilityResponse(BaseModel):
    file_ids: list[uuid.UUID]
    count: int


class SetKnowledgeTagsRequest(BaseModel):
    file_id: uuid.UUID
    tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    new_tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("new_tags")
    @classmethod
    def normalize_new_tags(cls, tags: list[str]) -> list[str]:
        normalized_tags = []
        seen_names = set()
        for tag in tags:
            name = tag.strip()
            if not name:
                raise ValueError("标签名称不能为空")
            if len(name) > 50:
                raise ValueError("标签名称不能超过 50 个字符")
            normalized_name = name.casefold()
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                normalized_tags.append(name)
        return normalized_tags


class AutoTagKnowledgeRequest(BaseModel):
    file_id: uuid.UUID
    max_tags: int = Field(default=5, ge=1, le=10)
    allow_new_tags: bool = True


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

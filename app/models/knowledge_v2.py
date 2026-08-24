import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.knowledge import RetrievalMethod


class KnowledgeV2TagResponse(BaseModel):
    id: uuid.UUID
    name: str


class KnowledgeV2TagsResponse(BaseModel):
    knowledge_id: uuid.UUID
    tags: list[KnowledgeV2TagResponse]


class SetKnowledgeV2TagsRequest(BaseModel):
    knowledge_id: uuid.UUID
    tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    new_tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("new_tags")
    @classmethod
    def normalize_new_tags(cls, values: list[str]) -> list[str]:
        return _normalize_tag_names(values)


class AutoTagKnowledgeV2Request(BaseModel):
    knowledge_id: uuid.UUID
    max_tags: int = Field(default=5, ge=1, le=10)
    allow_new_tags: bool = True


class KnowledgeV2FileIdsRequest(BaseModel):
    knowledge_ids: list[uuid.UUID] = Field(min_length=1)


class KnowledgeV2DatabaseResponse(BaseModel):
    id: uuid.UUID
    name: str


class KnowledgeV2FileResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    md5: str
    meta_data: dict[str, str]
    is_embedded: bool
    create_time: datetime | None
    uploader: str
    databases: list[KnowledgeV2DatabaseResponse] = Field(default_factory=list)
    tags: list[KnowledgeV2TagResponse] = Field(default_factory=list)


class KnowledgeV2PageResponse(BaseModel):
    items: list[KnowledgeV2FileResponse]
    page: int
    page_size: int
    total: int
    pages: int


class DeleteKnowledgeV2Response(BaseModel):
    id: uuid.UUID
    deleted: bool


class KnowledgeV2RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    database_name: str = Field(min_length=1)
    tag_names: list[str] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=10, ge=1, le=100)
    retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR
    semantic_weight: float = Field(default=0.7, ge=0, le=1)
    keyword_weight: float = Field(default=0.3, ge=0, le=1)

    @field_validator("database_name")
    @classmethod
    def strip_database_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("tag_names")
    @classmethod
    def normalize_tag_names(cls, values: list[str]) -> list[str]:
        normalized_values = []
        seen_values = set()
        for value in values:
            name = value.strip()
            if not name:
                raise ValueError("标签名称不能为空")
            normalized_name = name.casefold()
            if normalized_name not in seen_values:
                seen_values.add(normalized_name)
                normalized_values.append(name)
        return normalized_values

    @model_validator(mode="after")
    def validate_hybrid_weights(self) -> Self:
        if abs(self.semantic_weight + self.keyword_weight - 1) > 1e-6:
            raise ValueError("semantic_weight 与 keyword_weight 之和必须为 1")
        return self


class KnowledgeV2ChunkResponse(BaseModel):
    chunk_id: uuid.UUID
    knowledge_id: uuid.UUID
    filename: str
    chunk_index: int
    content: str
    meta_data: dict | None = None
    score: float
    semantic_score: float
    keyword_score: float | None = None
    retrieval_method: RetrievalMethod


class KnowledgeV2ChatRequest(KnowledgeV2RetrieveRequest):
    temperature: float = Field(default=0.2, ge=0, le=2)


class KnowledgeV2ChatResponse(BaseModel):
    answer: str
    chunks: list[KnowledgeV2ChunkResponse]


def _normalize_tag_names(values: list[str]) -> list[str]:
    normalized_values = []
    seen_values = set()
    for value in values:
        name = value.strip()
        if not name:
            raise ValueError("标签名称不能为空")
        if len(name) > 50:
            raise ValueError("标签名称不能超过 50 个字符")
        normalized_name = name.casefold()
        if normalized_name not in seen_values:
            seen_values.add(normalized_name)
            normalized_values.append(name)
    return normalized_values
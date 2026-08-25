import uuid
from datetime import datetime
from enum import Enum
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


class KnowledgeV2DatabaseDetailResponse(BaseModel):
    id: uuid.UUID
    database_name: str
    database_desc: str | None
    meta_data_template: list[str]


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


class DeleteQuestionLogResponse(BaseModel):
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
    score: float | None = None
    semantic_score: float | None = None
    keyword_score: float | None = None
    retrieval_method: RetrievalMethod | None = None


class KnowledgeV2ChatRequest(KnowledgeV2RetrieveRequest):
    temperature: float = Field(default=0.2, ge=0, le=2)


class KnowledgeV2ChatResponse(BaseModel):
    question_log_id: uuid.UUID
    answer: str
    chunks: list[KnowledgeV2ChunkResponse]


class QuestionFeedback(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    COLLECT = "collect"


class QuestionFeedbackRequest(BaseModel):
    feedback: QuestionFeedback


class QuestionLogResponse(BaseModel):
    id: uuid.UUID
    question: str
    answer: str | None
    related_chunkv2_ids: list[uuid.UUID]
    chunks: list[KnowledgeV2ChunkResponse] = Field(default_factory=list)
    user_feedback: QuestionFeedback | None
    create_time: datetime


class QuestionLogPageResponse(BaseModel):
    items: list[QuestionLogResponse]
    page: int
    page_size: int
    total: int
    pages: int


class SimilarQuestionRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("查询内容不能为空")
        return value


class SimilarQuestionResponse(QuestionLogResponse):
    score: float


class CreateKnowledgeV2RequirementRequest(BaseModel):
    related_log_id: uuid.UUID
    requirement: str | None = Field(default=None, max_length=2000)

    @field_validator("requirement")
    @classmethod
    def strip_requirement(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class KnowledgeV2RequirementStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class UpdateKnowledgeV2RequirementStatusRequest(BaseModel):
    status: KnowledgeV2RequirementStatus


class KnowledgeV2RequirementResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    owner_name: str
    requirement: str | None
    related_log_id: uuid.UUID | None
    question: str | None
    status: KnowledgeV2RequirementStatus
    is_resolved: bool
    related_knowledgev2_ids: list[uuid.UUID]
    create_time: datetime


class KnowledgeV2RequirementPageResponse(BaseModel):
    items: list[KnowledgeV2RequirementResponse]
    page: int
    page_size: int
    total: int
    pages: int


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
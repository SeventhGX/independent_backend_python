from datetime import datetime
import uuid

from pydantic import BaseModel, model_validator


class DocsCreateRequest(BaseModel):
    docs_name: str
    docs_desc: str | None = None
    content: str


class DocsUpdateRequest(BaseModel):
    docs_name: str | None = None
    docs_desc: str | None = None
    content: str | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        for field_name in ("docs_name", "content"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class DocsImageCreateRequest(BaseModel):
    docs_id: uuid.UUID | None = None
    image_name: str
    image_desc: str | None = None
    image_data: bytes


class DocsImageUpdateRequest(BaseModel):
    docs_id: uuid.UUID | None = None
    image_name: str | None = None
    image_desc: str | None = None
    image_data: bytes | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        for field_name in ("image_name", "image_data"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class DocsImageInfo(BaseModel):
    id: uuid.UUID
    docs_id: uuid.UUID | None = None
    image_name: str
    image_desc: str | None = None
    create_time: datetime | None = None
    create_by: uuid.UUID | None = None

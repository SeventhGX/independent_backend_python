from pydantic import BaseModel
import uuid


class GetFileRequest(BaseModel):
    id: uuid.UUID | None = None
    source_url: str | None = None
    filename: str | None = None
    file_type: str | None = None


class NewFileRequest(BaseModel):
    source_url: str | None = None
    filename: str | None = None
    file_type: str | None = None
    data: bytes


class FileResponse(BaseModel):
    id: uuid.UUID
    source_url: str | None = None
    filename: str | None = None
    file_type: str | None = None
    data: bytes

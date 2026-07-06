from pydantic import BaseModel
from sqlalchemy import Column, LargeBinary
from sqlmodel import Field
import uuid


class FileAddRequest(BaseModel):
    source_url: str | None = None
    filename: str | None = None
    file_type: str | None = None
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))

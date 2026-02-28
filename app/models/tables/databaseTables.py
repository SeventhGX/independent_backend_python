from datetime import datetime, date
import uuid
from sqlmodel import SQLModel, Field


class Article(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    url: str
    publish_time: datetime | None = None
    key_words: str | None = None
    summary: str | None = None
    content: str | None = None
    mail_date: date | None = None


class Recipient(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str
    name: str | None = None


class Sys_User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_code: str
    user_name: str
    password: str
    email: str | None = None
    phone: str | None = None
    last_login_time: datetime | None = None
    last_login_ip: str | None = None
    del_flag: bool = False
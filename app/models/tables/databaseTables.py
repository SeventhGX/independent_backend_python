from datetime import datetime, date
import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
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
    real_mail_date: date | None = None


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


class Chat_Session(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    session_name: str
    create_time: datetime | None = Field(default_factory=datetime.now)
    content: dict = Field(default=None, sa_column=Column(JSONB, nullable=True))


class Chat_Model(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_type: str
    model: str
    # sdk_type: str
    description: str | None = None
    del_flag: bool = False


class Chat_Model_V2(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_type: str
    model: str
    key_name: str
    sdk_type: str
    base_url: str
    kwargs: dict = Field(default=None, sa_column=Column(JSONB, nullable=True))
    description: str | None = None
    del_flag: bool = False


class User_Model_Cfg(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    model_v2_id: uuid.UUID
    cfg: dict = Field(default=None, sa_column=Column(JSONB, nullable=True))

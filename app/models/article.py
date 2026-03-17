from datetime import datetime, date
from pydantic import BaseModel


class ArticleBody(BaseModel):
    title: str
    url: str
    publish_time: datetime | None = None
    key_words: str | None = None
    summary: str | None = None
    content: str | None = None
    mail_date: date | None = None


class ArticleQueryBody(BaseModel):
    title: str | None = None
    url: str | None = None
    publish_time: datetime | None = None
    key_words: str | None = None
    summary: str | None = None
    content: str | None = None
    mail_date: date | None = None


class MailDataBody(BaseModel):
    sender_email: str = "rbmom@ronbaymat.com"
    sender_password: str = "GY4.0-mom"
    receiver_email: str | list[str] = []
    subject: str = "邮件主题"
    body: str = ""


class RecipientBody(BaseModel):
    email: str
    name: str | None = None


class ArticleDateRangeBody(BaseModel):
    publish_time_start: datetime | None = None
    publish_time_end: datetime | None = None
    mail_date_start: date | None = None
    mail_date_end: date | None = None
    real_mail_date_start: date | None = None
    real_mail_date_end: date | None = None

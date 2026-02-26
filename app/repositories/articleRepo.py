from app.models.tables.databaseTables import Article
from datetime import date
from app.utils.database import engine
from sqlmodel import Session, select
# from typing import Sequence


def select_all_articles():
    with Session(engine) as session:
        articles = session.exec(select(Article)).all()
        return articles


def select_articles_by_mail_date(mail_date: date):
    with Session(engine) as session:
        articles = session.exec(select(Article).where(Article.mail_date == mail_date)).all()
        return articles


def select_distinct_mail_dates() -> list[date | None]:
    with Session(engine) as session:
        mail_dates = session.exec(select(Article.mail_date).distinct()).all()  # type: ignore
        return mail_dates


def insert_article(article: Article):
    with Session(engine) as session:
        session.add(article)
        session.commit()
        session.refresh(article)
        return article

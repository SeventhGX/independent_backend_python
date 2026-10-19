import uuid
from datetime import date

from sqlmodel import Session, col, or_, select

from app.models.tables.databaseTables import Article, Search_Prompt_Template, Sys_User
from app.utils.database import engine

# from typing import Sequence


def select_all_articles():
    with Session(engine) as session:
        articles = session.exec(select(Article)).all()
        return articles


def select_article_by_args(**kwargs):
    with Session(engine) as session:
        query = select(Article)
        for key, value in kwargs.items():
            if value is not None:
                query = query.where(getattr(Article, key) == value)
        articles = session.exec(query).all()
        return articles


def select_article_by_range_args(**kwargs):
    with Session(engine) as session:
        query = select(Article)
        for key, value in kwargs.items():
            if value is not None:
                if key.endswith("_start"):
                    field_name = key[:-6]
                    query = query.where(getattr(Article, field_name) >= value)
                elif key.endswith("_end"):
                    field_name = key[:-4]
                    query = query.where(getattr(Article, field_name) <= value)
        # print(query)  # 调试输出生成的查询语句
        articles = session.exec(query).all()
        return articles


def select_articles_by_mail_date(mail_date: date):
    with Session(engine) as session:
        articles = session.exec(
            select(Article).where(or_(Article.mail_date == mail_date, col(Article.mail_date).is_(None)))
        ).all()
        return articles


def select_distinct_mail_dates() -> list[date | None]:
    with Session(engine) as session:
        mail_dates = session.exec(select(Article.mail_date).distinct()).all()  # type: ignore
        return mail_dates


def insert_article(article: Article):
    with Session(engine) as session:
        exist = session.exec(
            select(Article).where(or_(Article.url == article.url, Article.title == article.title))
        ).first()
        if exist:
            return exist
        session.add(article)
        session.commit()
        session.refresh(article)
        return article


def update_article_date(article_id: str, real_mail_date: date):
    with Session(engine) as session:
        article = session.get(Article, article_id)
        if article:
            article.real_mail_date = real_mail_date
            session.add(article)
            session.commit()
            session.refresh(article)
            return article
        else:
            return None


def select_search_prompt_templates(
    template_name: str | None = None,
) -> list[tuple[Search_Prompt_Template, str | None]]:
    with Session(engine) as session:
        query = select(Search_Prompt_Template, Sys_User.user_name).outerjoin(
            Sys_User, col(Sys_User.id) == col(Search_Prompt_Template.user_id)
        )
        if template_name:
            query = query.where(col(Search_Prompt_Template.template_name).ilike(f"%{template_name}%"))
        query = query.order_by(col(Search_Prompt_Template.create_time).desc())
        return list(session.exec(query).all())


def insert_search_prompt_template(template: Search_Prompt_Template):
    with Session(engine) as session:
        session.add(template)
        session.commit()
        session.refresh(template)
        return template


def delete_search_prompt_template(template_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        template = session.get(Search_Prompt_Template, template_id)
        if template is None:
            return False
        if template.user_id != user_id:
            raise PermissionError("只能删除自己创建的提示词模版")
        session.delete(template)
        session.commit()
        return True

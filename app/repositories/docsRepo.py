from datetime import datetime
from typing import cast
import uuid

from sqlalchemy import delete, select as sqlalchemy_select
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlmodel import Session, col, select

from app.models.tables.databaseTables import Docs, DocsImage
from app.utils.database import engine


def select_all_docs():
    with Session(engine) as session:
        return session.exec(select(Docs).order_by(col(Docs.update_time).desc())).all()


def select_docs_by_id(docs_id: uuid.UUID):
    with Session(engine) as session:
        return session.get(Docs, docs_id)


def insert_docs(docs: Docs):
    with Session(engine) as session:
        session.add(docs)
        session.commit()
        session.refresh(docs)
        return docs


def update_docs(docs_id: uuid.UUID, values: dict):
    with Session(engine) as session:
        docs = session.get(Docs, docs_id)
        if docs is None:
            return None
        for key, value in values.items():
            setattr(docs, key, value)
        docs.update_time = datetime.now()
        session.add(docs)
        session.commit()
        session.refresh(docs)
        return docs


def delete_docs(docs_id: uuid.UUID):
    with Session(engine) as session:
        docs = session.get(Docs, docs_id)
        if docs is None:
            return False
        session.exec(delete(DocsImage).where(col(DocsImage.docs_id) == docs_id))
        session.delete(docs)
        session.commit()
        return True


def select_image_info(docs_id: uuid.UUID | None = None):
    with Session(engine) as session:
        statement = sqlalchemy_select(
            col(DocsImage.id),
            col(DocsImage.docs_id),
            col(DocsImage.image_name),
            col(DocsImage.image_desc),
            col(DocsImage.create_time),
            col(DocsImage.create_by),
        ).order_by(col(DocsImage.create_time).desc())
        if docs_id is not None:
            statement = statement.where(col(DocsImage.docs_id) == docs_id)
        return cast(SQLAlchemySession, session).execute(statement).all()


def select_image_by_id(image_id: uuid.UUID):
    with Session(engine) as session:
        return session.get(DocsImage, image_id)


def insert_image(image: DocsImage):
    with Session(engine) as session:
        session.add(image)
        session.commit()
        session.refresh(image)
        return image


def update_image(image_id: uuid.UUID, values: dict):
    with Session(engine) as session:
        image = session.get(DocsImage, image_id)
        if image is None:
            return None
        for key, value in values.items():
            setattr(image, key, value)
        session.add(image)
        session.commit()
        session.refresh(image)
        return image


def delete_image(image_id: uuid.UUID):
    with Session(engine) as session:
        image = session.get(DocsImage, image_id)
        if image is None:
            return False
        session.delete(image)
        session.commit()
        return True

import uuid
from typing import Any, cast

from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.models.tables.databaseTables import Chunks, File, Knowledge
from app.utils.database import engine


def insert_knowledge_file(file: File, knowledge: Knowledge):
    with Session(engine) as session:
        session.add(file)
        session.flush()

        knowledge.file_id = file.id
        session.add(knowledge)
        session.commit()
        session.refresh(file)
        session.refresh(knowledge)
        return file, knowledge


def select_knowledge_by_user_id(user_id: uuid.UUID):
    with Session(engine) as session:
        statement = (
            select(Knowledge, File)
            .join(File, col(Knowledge.file_id) == File.id)
            .where(Knowledge.user_id == user_id)
            .order_by(col(Knowledge.create_time).desc())
        )
        return session.exec(statement).all()


def select_knowledge_by_file_ids(file_ids: list[uuid.UUID], user_id: uuid.UUID | None = None):
    if not file_ids:
        return []
    with Session(engine) as session:
        statement = select(Knowledge).where(col(Knowledge.file_id).in_(file_ids))
        if user_id is not None:
            statement = statement.where(Knowledge.user_id == user_id)
        statement = statement.order_by(col(Knowledge.create_time).desc())
        return session.exec(statement).all()


def replace_file_chunks(file_id: uuid.UUID, chunks: list[Chunks]):
    with Session(engine) as session:
        session.exec(delete(Chunks).where(col(Chunks.file_id) == file_id))
        session.add_all(chunks)
        knowledge = session.exec(select(Knowledge).where(col(Knowledge.file_id) == file_id)).first()
        if knowledge:
            knowledge.is_embedded = True
            session.add(knowledge)
        session.commit()
        return len(chunks)


def search_similar_chunks(
    query_embedding: list[float],
    user_id: uuid.UUID,
    file_ids: list[uuid.UUID] | None = None,
    top_k: int = 5,
):
    with Session(engine) as session:
        distance = cast(Any, Chunks.embedding).cosine_distance(query_embedding).label("distance")
        statement = (
            select(Chunks, distance)
            .join(Knowledge, col(Chunks.file_id) == col(Knowledge.file_id))
            .where(Knowledge.user_id == user_id)
            .where(col(Chunks.embedding).is_not(None))
            .order_by(distance)
            .limit(top_k)
        )
        if file_ids:
            statement = statement.where(col(Chunks.file_id).in_(file_ids))
        return session.exec(statement).all()


def delete_knowledge_files(file_ids: list[uuid.UUID], user_id: uuid.UUID):
    if not file_ids:
        return []

    with Session(engine) as session:
        owned_file_ids = session.exec(
            select(Knowledge.file_id)
            .where(Knowledge.user_id == user_id)
            .where(col(Knowledge.file_id).in_(file_ids))
        ).all()
        if not owned_file_ids:
            return []

        session.exec(delete(Chunks).where(col(Chunks.file_id).in_(owned_file_ids)))
        session.exec(delete(Knowledge).where(col(Knowledge.file_id).in_(owned_file_ids)))
        session.exec(delete(File).where(col(File.id).in_(owned_file_ids)))
        session.commit()
        return owned_file_ids

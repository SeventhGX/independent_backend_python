from app.models.tables.databaseTables import Chunks, File, Knowledge
from app.utils.database import engine
from sqlalchemy import delete
from sqlmodel import Session, col, select
import uuid


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

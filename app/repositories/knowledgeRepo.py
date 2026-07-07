from app.models.tables.databaseTables import File, Knowledge
from app.utils.database import engine
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
        )
        return session.exec(statement).all()

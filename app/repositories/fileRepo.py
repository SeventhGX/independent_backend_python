from app.models.tables.databaseTables import File
import uuid
from app.utils.database import engine
from sqlmodel import Session, select


def insert_file(file: File):
    with Session(engine) as db_session:
        db_session.add(file)
        db_session.commit()
        db_session.refresh(file)
        return file


def select_file_by_id(file_id: uuid.UUID):
    with Session(engine) as session:
        return session.exec(select(File).where(File.id == file_id)).first()

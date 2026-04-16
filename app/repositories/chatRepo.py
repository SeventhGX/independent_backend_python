from app.models.tables.databaseTables import Chat_Session
import uuid
from app.utils.database import engine
from sqlmodel import Session, select, col


def select_sessions_by_user_id(user_id: uuid.UUID):
    with Session(engine) as session:
        sessions = session.exec(
            select(Chat_Session)
            .where(Chat_Session.user_id == user_id)
            .order_by(col(Chat_Session.create_time).desc())
        ).all()
        return sessions


def insert_chat_session(session: Chat_Session):
    with Session(engine) as db_session:
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session


def update_chat_session_content(session_id: uuid.UUID, content: dict):
    with Session(engine) as db_session:
        session = db_session.exec(select(Chat_Session).where(Chat_Session.id == session_id)).first()
        if session:
            session.content = content
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)
            return session
        else:
            return None

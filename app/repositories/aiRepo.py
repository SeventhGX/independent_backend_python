from app.models.tables.databaseTables import Chat_Session, Chat_Model, Chat_Model_V2, User_Model_Cfg
import uuid
from app.utils.database import engine
from sqlmodel import Session, select, col


def select_sessions_by_user_id(user_id: uuid.UUID):
    with Session(engine) as session:
        rows = session.exec(
            select(Chat_Session.id, Chat_Session.session_name, Chat_Session.create_time)
            .where(Chat_Session.user_id == user_id)
            .order_by(col(Chat_Session.create_time).desc())
        ).all()
        return [{"id": row[0], "session_name": row[1], "create_time": row[2]} for row in rows]


def select_sessions_by_session_id(session_id: uuid.UUID):
    with Session(engine) as session:
        session = session.exec(select(Chat_Session).where(Chat_Session.id == session_id)).first()
        return session


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


def select_models():
    with Session(engine) as session:
        models = session.exec(select(Chat_Model).where(Chat_Model.del_flag == False)).all()  # noqa: E712
        # print(models)
        return models


def select_models_v2():
    with Session(engine) as session:
        models2 = session.exec(select(Chat_Model_V2).where(Chat_Model_V2.del_flag == False)).all()  # noqa: E712
        return models2


def select_user_model_cfg_map(user_id: uuid.UUID, model_v2_ids: list[uuid.UUID]):
    if not model_v2_ids:
        return {}

    with Session(engine) as session:
        cfg_rows = session.exec(
            select(User_Model_Cfg).where(
                User_Model_Cfg.user_id == user_id,
                col(User_Model_Cfg.model_v2_id).in_(model_v2_ids),
            )
        ).all()
        return {row.model_v2_id: row.cfg for row in cfg_rows}

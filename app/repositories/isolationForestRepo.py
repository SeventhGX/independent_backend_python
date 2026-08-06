import uuid

from sqlmodel import Session, select

from app.models.tables.databaseTables import IsolationForestResult
from app.utils.database import engine


def insert_result(result: IsolationForestResult) -> IsolationForestResult:
    with Session(engine) as session:
        session.add(result)
        session.commit()
        session.refresh(result)
        return result


def select_result_by_id_and_user_id(
    result_id: uuid.UUID,
    user_id: uuid.UUID,
) -> IsolationForestResult | None:
    with Session(engine) as session:
        return session.exec(
            select(IsolationForestResult).where(
                IsolationForestResult.id == result_id,
                IsolationForestResult.user_id == user_id,
            )
        ).first()
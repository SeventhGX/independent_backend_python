import uuid

from sqlmodel import Session, select

from app.models.tables.databaseTables import AStarResult
from app.utils.database import engine


def insert_result(result: AStarResult) -> AStarResult:
    with Session(engine) as session:
        session.add(result)
        session.commit()
        session.refresh(result)
        return result


def select_result_by_id_and_user_id(
    result_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AStarResult | None:
    with Session(engine) as session:
        return session.exec(
            select(AStarResult).where(
                AStarResult.id == result_id,
                AStarResult.user_id == user_id,
            )
        ).first()
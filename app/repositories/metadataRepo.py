from sqlmodel import Session, col, select

from app.models.tables.databaseTables import Metadata
from app.utils.database import engine


def select_all_metadata():
    with Session(engine) as session:
        return session.exec(
            select(Metadata).order_by(
                col(Metadata.field_name),
                col(Metadata.value),
            )
        ).all()
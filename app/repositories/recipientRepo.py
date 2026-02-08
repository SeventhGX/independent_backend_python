from app.models.tables.databaseTables import Article, Recipient
from app.utils.database import engine
from sqlmodel import Session, select


def select_all_recipients():
    with Session(engine) as session:
        recipients = session.exec(select(Recipient)).all()
        return recipients


def insert_recipient(recipient: Recipient):
    with Session(engine) as session:
        session.add(recipient)
        session.commit()
        session.refresh(recipient)
        return recipient

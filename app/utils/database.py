from app.utils.config import settings
from app.utils.log import logger
from sqlmodel import SQLModel, create_engine
from app.models.tables.databaseTables import *

engine = create_engine(str(settings.DATABASE_URI))


def init_db():
    logger.debug(settings.DATABASE_URI)
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
    # with Session(engine) as session:
    #     article = Article(
    #         title="Sample Article",
    #         url="http://example.com/sample-article",
    #         summary="This is a sample article for database initialization.",
    #     )
    #     session.add(article)
    #     session.commit()

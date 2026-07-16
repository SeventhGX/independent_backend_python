from app.utils.config import settings
from app.utils.log import logger
from sqlmodel import SQLModel, create_engine, select, Session
from app.models.tables.databaseTables import *

from pwdlib import PasswordHash

# ---------------------------------------------------------------------------
# 数据库连接
# ---------------------------------------------------------------------------

engine = create_engine(str(settings.DATABASE_URI))


# ---------------------------------------------------------------------------
# 数据库初始化
# ---------------------------------------------------------------------------


def init_db():
    """创建数据库表结构，并在缺失时初始化默认管理员账号。"""
    logger.debug(settings.DATABASE_URI)
    logger.info("初始化数据库...")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin_user = session.exec(
            select(Sys_User).where(Sys_User.user_name == "admin", Sys_User.user_code == "00000000")
        ).first()
        if not admin_user:
            logger.info("初始化数据库...")
            logger.info("创建默认管理员账号...")
            password_hash = PasswordHash.recommended().hash("admin123")
            admin_user = Sys_User(
                user_code="00000000",
                user_name="admin",
                password=password_hash,
            )
            session.add(admin_user)
            session.commit()
            logger.info("默认管理员账号(00000000;admin;admin123)创建成功！")
            logger.info("数据库初始化完成！")
    logger.info("数据库初始化完成！")


# 根据配置决定应用启动时是否自动执行建表和默认账号初始化。
if settings.INITIALIZE_DB:
    init_db()


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

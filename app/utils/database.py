from pwdlib import PasswordHash
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.tables.databaseTables import DEFAULT_ADMIN_USER_CODE, Database, Metadata, Sys_User
from app.utils.config import settings
from app.utils.log import logger

# ---------------------------------------------------------------------------
# 数据库连接
# ---------------------------------------------------------------------------

engine = create_engine(str(settings.DATABASE_URI))


# ---------------------------------------------------------------------------
# 数据库初始化
# ---------------------------------------------------------------------------


def init_db():
    """创建数据库表结构，并在缺失时初始化默认管理员账号和元数据。"""
    logger.debug(settings.DATABASE_URI)
    logger.info("初始化数据库...")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin_user = session.exec(
            select(Sys_User).where(
                Sys_User.user_name == "admin",
                Sys_User.user_code == DEFAULT_ADMIN_USER_CODE,
            )
        ).first()
        if not admin_user:
            logger.info("初始化数据库...")
            logger.info("创建默认管理员账号...")
            password_hash = PasswordHash.recommended().hash("admin123")
            admin_user = Sys_User(
                user_code=DEFAULT_ADMIN_USER_CODE,
                user_name="admin",
                password=password_hash,
            )
            session.add(admin_user)
            session.commit()
            logger.info("默认管理员账号(00000000;admin;admin123)创建成功！")
            logger.info("数据库初始化完成！")

        metadata = session.exec(select(Metadata).limit(1)).first()
        if metadata is None:
            logger.info("创建默认元数据...")
            initial_metadata: list[Metadata] = [
                Metadata(field_name="position", field_desc="岗位", value="TL", desc="投料"),
                Metadata(field_name="page", field_desc="页面", value="knowledge", desc="知识库"),
                Metadata(field_name="equipment", field_desc="设备", value="YL", desc="窑炉"),
            ]
            session.add_all(initial_metadata)
            session.commit()
            logger.info("默认元数据创建成功！")

        databases = session.exec(select(Database).limit(1)).first()
        if databases is None:
            logger.info("创建默认知识库...")
            initial_databases: list[Database] = [
                Database(database_name="sop", database_desc="岗位SOP", meta_data_template=["position"]),
                Database(database_name="sys", database_desc="系统操作指南", meta_data_template=["page"]),
                Database(database_name="repair", database_desc="维修手册", meta_data_template=["equipment"]),
            ]
            session.add_all(initial_databases)
            session.commit()
            logger.info("默认知识库创建成功！")
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

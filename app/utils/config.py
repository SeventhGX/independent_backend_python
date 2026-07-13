from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field

# ---------------------------------------------------------------------------
# 应用配置
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """从 .env 和环境变量加载应用运行所需配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    DEEPSEEK_API_KEY: str
    DOUBAO_API_KEY: str
    DOUBAO_CRAWLER_BOT_ID: str
    GPT_API_KEY: str
    QWEN_EMBEDDING_API_KEY: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str
    INITIALIZE_DB: bool
    CHROME_DRIVER_PATH: str | None = None
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @computed_field
    @property
    def DATABASE_URI(self) -> PostgresDsn:
        """根据数据库连接参数拼装 SQLModel 使用的 PostgreSQL DSN。"""
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            path=self.DATABASE_NAME,
        )


# 全局配置实例，供 API、服务、仓储和工具模块统一引用。
settings = Settings()  # type: ignore

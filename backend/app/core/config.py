"""全局配置：通过环境变量 / .env 注入，Pydantic Settings 校验。"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    app_name: str = "SOG 离散装配生产作业支援系统"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # PostgreSQL 18
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "sog"
    db_user: str = "sog"
    db_password: str = "sog_pass"
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False

    # 并发
    worker_threads: int = 16
    async_concurrency: int = 32

    redis_url: str = ""
    cors_origins: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        """psycopg3 异步连接串：postgresql+psycopg://。"""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

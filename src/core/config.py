from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent

    PATH_TO_DB: Path = BASE_DIR / "test.db"  # ":memory:"

    PATH_TO_EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "notifications" / "templates")
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"

    EMAIL_HOST: str = "127.0.0.1"
    EMAIL_PORT: int = 1025
    EMAIL_HOST_USER: str = "testuser"
    EMAIL_HOST_PASSWORD: str = "test_password"
    EMAIL_USE_TLS: bool = False
    MAILHOG_API_PORT: int = 8025


class Settings(BaseAppSettings):
    POSTGRES_USER: str = "test_user"
    POSTGRES_PASSWORD: str = "<PASSWORD>"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_DB_PORT: int = 5555
    POSTGRES_DB: str = "test_db"

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env.local")


class TestingSettings(BaseAppSettings):

    def model_post_init(self, __context: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, "PATH_TO_DB", "test.db")

    @property
    def database_url_async(self) -> str:
        return f"sqlite+aiosqlite:///{self.PATH_TO_DB}"

    model_config = SettingsConfigDict(env_file=None)

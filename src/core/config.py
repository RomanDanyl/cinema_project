from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: Path = BASE_DIR / "test.db"  # ":memory:"
    BASE_URL: str = "http://127.0.0.1:8000"

    PATH_TO_EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "notifications" / "templates")
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"

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
    POSTGRES_DB_PORT: int = 5435
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

    model_config = SettingsConfigDict(env_file=".env")


class TestingSettings(BaseAppSettings):

    @property
    def database_url_async(self) -> str:
        return f"sqlite+aiosqlite:///{self.PATH_TO_DB}"

    model_config = SettingsConfigDict(env_file=None)

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.dependencies import get_settings


settings = get_settings()


engine = create_async_engine(
    settings.database_url_async,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_postgresql_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency provider for FastAPI.
    Yields an async session and automatically closes it after the request.
    """
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_postgresql_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for manual session management.
    Used in tests, background tasks, or scripts where FastAPI dependency injection is unavailable.
    """
    async with AsyncSessionLocal() as session:
        yield session

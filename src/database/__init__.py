import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session_sqlite3 import reset_sqlite_database as reset_database

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from src.database.session_sqlite3 import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db
    )
else:
    from src.database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )

SessionDep = Annotated[AsyncSession, Depends(get_db)]

__all__ = [
    "get_db",
    "get_db_contextmanager",
    "reset_database",
    "SessionDep"
]

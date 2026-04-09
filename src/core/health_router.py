import httpx
from fastapi import APIRouter, status
from sqlalchemy import text
from typing import Dict, Any

from src.database.session_postgresql import PostgresSessionDep
from src.core.dependencies import SettingsDep

router = APIRouter(prefix="/health", tags=["system"])


async def check_mailhog(settings) -> str:
    """Check Mailhog available within its API."""
    url = f"http://{settings.EMAIL_HOST}:8025/api/v2/messages"
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get(url)
            return "ok" if response.status_code == 200 else "error"
    except Exception:
        return "unreachable"


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check(
    db: PostgresSessionDep,
    settings: SettingsDep
) -> Dict[str, Any]:
    """
    Complex system health check.
    """
    health_status = {
        "status": "ok",
        "components": {
            "python_app": "ok",
            "database": "loading",
            "mailhog": "loading"
        }
    }

    try:
        await db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "ok"
    except Exception:
        health_status["components"]["database"] = "error"
        health_status["status"] = "unhealthy"

    mail_status = await check_mailhog(settings)
    health_status["components"]["mailhog"] = mail_status
    if mail_status != "ok":
        health_status["status"] = "unhealthy"
    return health_status

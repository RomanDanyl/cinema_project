from fastapi import FastAPI

from src.auth.routes import router as auth_router
from src.core.health_router import router as health_router

app = FastAPI()

api_version_prefix = "/api/v1"

app.include_router(health_router)
app.include_router(auth_router, prefix=api_version_prefix, tags=["accounts"])

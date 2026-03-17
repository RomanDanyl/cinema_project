from fastapi import FastAPI

from src.auth import auth_router

app = FastAPI()

api_version_prefix = "/api/v1"

app.include_router(auth_router, prefix=api_version_prefix, tags=["accounts"])

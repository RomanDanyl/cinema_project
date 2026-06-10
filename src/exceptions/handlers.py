from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.exceptions.passwords import PasswordStrengthError

async def password_error_handler(request: Request, exc: PasswordStrengthError) -> JSONResponse:
    """
    Global exception handler for PasswordStrengthError.
    Transforms model validation errors into standard FastAPI 422 responses.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": [
                {
                    "loc": ["body", "password"],
                    "msg": str(exc),
                    "type": "value_error"
                }
            ]
        },
    )

from fastapi import FastAPI

from src.exceptions.emails import BaseEmailError
from src.exceptions.security import BaseSecurityError, TokenExpiredError, InvalidTokenError
from src.exceptions.passwords import PasswordStrengthError
from src.exceptions.handlers import password_error_handler


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers to the FastAPI application.
    """
    app.add_exception_handler(PasswordStrengthError, password_error_handler)

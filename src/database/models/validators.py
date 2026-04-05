import re

import email_validator

from src.exceptions.passwords import PasswordStrengthError


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise PasswordStrengthError("Password must contain at least 8 characters.")
    if not re.search(r'[A-Z]', password):
        raise PasswordStrengthError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise PasswordStrengthError("Password must contain at least one lower letter.")
    if not re.search(r'\d', password):
        raise PasswordStrengthError("Password must contain at least one digit.")
    if not re.search(r'[@$!%*?&#]', password):
        raise PasswordStrengthError("Password must contain at least one special character: @, $, !, %, *, ?, #, &.")
    return password


def validate_email(user_email: str) -> str:
    try:
        email_info = email_validator.validate_email(user_email, check_deliverability=False)
        email = email_info.normalized
    except email_validator.EmailNotValidError as error:
        raise ValueError(str(error))
    else:
        return email

from datetime import datetime, timezone

from fastapi import APIRouter, status, HTTPException, BackgroundTasks, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload

from src.database.session_postgresql import PostgresSessionDep
from src.exceptions import BaseEmailError
from src.core.dependencies import EmailSenderDep, SettingsDep, TokenManagerDep
from src.database.models import UserModel, ActivationTokenModel, RefreshTokenModel
from src.auth.schemas import UserRegistrationResponseSchema, UserRegistrationRequestSchema, UserLoginResponseSchema, \
    UserLoginRequestSchema, MessageResponseSchema

router = APIRouter(prefix="/accounts")


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred during user creation."}
                }
            },
        },
    },
)
async def register_user(
    user_data: UserRegistrationRequestSchema,
    db: PostgresSessionDep,
    email_sender: EmailSenderDep,
    settings: SettingsDep,
    background_tasks: BackgroundTasks
) -> UserRegistrationResponseSchema:
    try:
        async with db.begin():
            new_user = UserModel.create(
                email=user_data.email,
                raw_password=user_data.password,
            )
            db.add(new_user)
            await db.flush()

            activation_token = ActivationTokenModel(user_id=new_user.id)
            db.add(activation_token)
            await db.flush()

            base = settings.BASE_URL.rstrip("/")
            activation_link = f"{base}/api/v1/accounts/activate/?token={activation_token.token}"

            background_tasks.add_task(
                email_sender.send_activation_email,
                new_user.email,
                activation_link
            )

        await db.refresh(new_user)

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists.",
        )
    except (SQLAlchemyError, BaseEmailError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        )

    return UserRegistrationResponseSchema.model_validate(new_user)


@router.get(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="Activate User Account",
    description="Activate a user's account using their activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
            "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {"detail": "Invalid or expired activation token."},
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {"detail": "User account is already active."},
                        },
                    }
                }
            },
        },
    },
)
async def activate_account(
    db: PostgresSessionDep,
    email_sender: EmailSenderDep,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    token: str = Query(..., description="The activation token from the email"),
) -> MessageResponseSchema:
    """
        Endpoint to activate a user's account.

        This endpoint verifies the activation token for a user by checking that the token record exists
        and that it has not expired, then sends a confirmation email as a background task upon
        successful activation If the token is valid and the user's account is not already active,
        the user's account is activated and the activation token is deleted. If the token is invalid, expired,
        or if the account is already active, an HTTP 400 error is raised.

        Args:
            token: Contains the user's token.
            db (AsyncSession): The asynchronous database session.
            email_sender (EmailSenderInterface): The asynchronous email sender.
            background_tasks(BackgroundTasks): FastAPI manager for non-blocking post-response tasks.
            settings (SettingsDep): The FastAPI settings object.

        Returns:
            MessageResponseSchema: A response message confirming successful activation.

        Raises:
            HTTPException:
                - 400 Bad Request if the activation token is invalid or expired.
                - 400 Bad Request if the user account is already active.
    """
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .where(ActivationTokenModel.token == token)
    )
    result = await db.execute(stmt)
    token_record = result.unique().scalar_one_or_none()

    now_utc = datetime.now(timezone.utc)

    if not token_record or token_record.expires_at.replace(tzinfo=timezone.utc) < now_utc:
        if token_record:
            await db.delete(token_record)
            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    user = token_record.user

    if user.is_active:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    base = settings.BASE_URL.rstrip("/")
    login_link = f"{base}/api/v1/accounts/login/"
    background_tasks.add_task(
        email_sender.send_activation_complete_email,
        user.email,
        login_link
    )

    return MessageResponseSchema(message=f"User account activated successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email or password."}
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {"detail": "User account is not activated."}
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    },
)
async def login_user(
    login_data: UserLoginRequestSchema,
    db: PostgresSessionDep,
    settings: SettingsDep,
    jwt_manager: TokenManagerDep,
) -> UserLoginResponseSchema:
    """
    Endpoint for user login.

    Authenticates a user using their email and password.
    If authentication is successful, creates a new refresh token and returns both access and refresh tokens.

    Args:
        login_data (UserLoginRequestSchema): The login credentials.
        db (AsyncSession): The asynchronous database session.
        settings (BaseAppSettings): The application settings.
        jwt_manager (JWTAuthManagerInterface): The JWT authentication manager.

    Returns:
        UserLoginResponseSchema: A response containing the access and refresh tokens.

    Raises:
        HTTPException:
            - 401 Unauthorized if the email or password is invalid.
            - 403 Forbidden if the user account is not activated.
            - 500 Internal Server Error if an error occurs during token creation.
    """
    stmt = select(UserModel).filter_by(email=login_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token = RefreshTokenModel.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token,
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
    )

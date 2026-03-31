from fastapi import APIRouter, status, HTTPException, BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.exceptions import BaseEmailError
from src.core.dependencies import EmailSenderDep, SettingsDep
from src.database.models import UserModel, ActivationTokenModel
from src.database import SessionDep
from src.auth.schemas import UserRegistrationResponseSchema, UserRegistrationRequestSchema

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
    db: SessionDep,
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

import httpx
import pytest
from bs4 import BeautifulSoup
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.auth.models import ActivationTokenModel, UserModel, RefreshTokenModel


@pytest.mark.e2e
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_registration(e2e_client, reset_db_once_for_e2e, settings, e2e_db_session):
    """
    End-to-end test for user registration.

    This test verifies the following:
    1. A user can successfully register with valid credentials.
    2. An activation email is sent to the provided email address.
    3. The email contains the correct activation link.

    Steps:
    - Send a POST request to the registration endpoint with user data.
    - Assert the response status code and returned user data.
    - Fetch the list of emails from MailHog via its API.
    - Verify that an email was sent to the expected recipient.
    - Ensure the email body contains the activation link.
    """
    user_data = {
        "email": "test@mate.com",
        "password": "StrongPassword123!"
    }
    response = await e2e_client.post("/api/v1/accounts/register/", json=user_data)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    response_data = response.json()
    assert response_data["email"] == user_data["email"]

    mailhog_url = f"http://{settings.EMAIL_HOST}:{settings.MAILHOG_API_PORT}/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)

    await e2e_db_session.commit()
    e2e_db_session.expire_all()

    assert mailhog_response.status_code == 200, f"MailHog API returned {mailhog_response.status_code}"
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No emails were sent!"

    email = messages[0]
    assert email["Content"]["Headers"]["To"][0] == user_data["email"], "Email recipient does not match."

    email_html = email["Content"]["Body"]
    email_subject = email["Content"]["Headers"].get("Subject", [None])[0]
    assert email_subject == "Account Activation", f"Expected subject 'Account Activation', but got '{email_subject}'"

    soup = BeautifulSoup(email_html, "html.parser")
    email_element = soup.find("strong", id="email")
    assert email_element is not None, "Email element with id 'email' not found!"
    try:
        validate_email(email_element.text)
    except EmailNotValidError as e:
        pytest.fail(f"The email link {email_element.text} is not valid: {e}")
    assert email_element.text == user_data["email"], "Email content does not match!"

    link_element = soup.find("a", id="link")
    assert link_element is not None, "Activation link element with id 'link' not found!"
    activation_url = link_element["href"]
    assert "/api/v1/accounts/activate/?token=" in activation_url, f"The URL '{activation_url}' is not valid!"


@pytest.mark.e2e
@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_account_activation(e2e_client, settings, e2e_db_session):
    """
    End-to-end test for account activation.

    This test verifies the following:
    1. The activation token is valid.
    2. The account can be activated using the token.
    3. The account's status is updated to active in the database.
    4. An email confirming activation is sent to the user.

    Steps:
    - Retrieve the activation token from the database.
    - Send a GET request to the activation endpoint with the token.
    - Assert the response status code and verify the account is activated.
    - Fetch the list of emails from MailHog via its API.
    - Verify the email sent confirms the activation and contains the expected details.
    """
    user_email = "test@mate.com"

    stmt = (
        select(ActivationTokenModel)
        .join(UserModel)
        .where(UserModel.email == user_email)
    )
    result = await e2e_db_session.execute(stmt)
    activation_token_record = result.scalars().first()
    assert activation_token_record, f"Activation token for email {user_email} not found!"
    token_value = activation_token_record.token

    activation_url = f"/api/v1/accounts/activate/?token={token_value}"
    response = await e2e_client.get(activation_url)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    response_data = response.json()
    assert response_data["message"] == "User account activated successfully.", "Unexpected activation message!"

    await e2e_db_session.commit()

    stmt_user = select(UserModel).where(UserModel.email == user_email)
    result_user = await e2e_db_session.execute(stmt_user)
    activated_user = result_user.scalars().first()
    assert activated_user.is_active, f"User {user_email} is not active!"

    mailhog_url = f"http://{settings.EMAIL_HOST}:{settings.MAILHOG_API_PORT}/api/v2/messages"
    async with httpx.AsyncClient() as client:
        mailhog_response = await client.get(mailhog_url)
    assert mailhog_response.status_code == 200, "Failed to fetch emails from MailHog!"
    messages = mailhog_response.json()["items"]
    assert len(messages) > 0, "No emails were sent!"

    email = messages[0]
    assert email["Content"]["Headers"]["To"][0] == user_email, "Recipient email does not match!"
    email_subject = email["Content"]["Headers"].get("Subject", [None])[0]
    assert email_subject == "Account Activated Successfully", \
        f"Expected subject 'Account Activated Successfully', but got '{email_subject}'"

    email_html = email["Content"]["Body"]
    soup = BeautifulSoup(email_html, "html.parser")

    email_element = soup.find("strong", id="email")
    assert email_element is not None, "Email element with id 'email' not found!"
    try:
        validate_email(email_element.text)
    except EmailNotValidError as e:
        pytest.fail(f"The email link {email_element.text} is not valid: {e}")
    assert email_element.text == user_email, "Email content does not match the user's email!"

    link_element = soup.find("a", id="link")
    assert link_element is not None, "Login link element with id 'link' not found!"
    login_url = link_element["href"]
    assert "api/v1/accounts/login/" in login_url, f"The URL '{login_url}' is not valid!"


@pytest.mark.e2e
@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_user_login(e2e_client, e2e_db_session):
    """
    End-to-end test for user login (async version).

    This test verifies the following:
    1. A user can log in with valid credentials.
    2. The API returns an access token and a refresh token.
    3. The refresh token is stored in the database.

    Steps:
    - Send a POST request to the login endpoint with the user's credentials.
    - Assert the response status code and verify the returned access and refresh tokens.
    - Validate that the refresh token is stored in the database.
    """
    user_data = {
        "email": "test@mate.com",
        "password": "StrongPassword123!"
    }

    login_url = "/api/v1/accounts/login/"
    response = await e2e_client.post(login_url, json=user_data)

    assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
    response_data = response.json()

    assert "access_token" in response_data, "Access token is missing in the response!"
    assert "refresh_token" in response_data, "Refresh token is missing in the response!"

    refresh_token = response_data["refresh_token"]

    stmt = (
        select(RefreshTokenModel)
        .options(joinedload(RefreshTokenModel.user))
        .where(RefreshTokenModel.token == refresh_token)
    )
    result = await e2e_db_session.execute(stmt)
    stored_token = result.scalars().first()

    assert stored_token is not None, "Refresh token was not stored in the database!"
    assert stored_token.user.email == user_data["email"], "Refresh token is linked to the wrong user!"

import httpx
import pytest
from bs4 import BeautifulSoup
from email_validator import validate_email, EmailNotValidError


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

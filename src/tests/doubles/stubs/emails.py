from src.notifications.interfaces import EmailSenderInterface


class StubEmailSender(EmailSenderInterface):

    async def send_activation_email(self, email: str, activation_link: str) -> None:
        """
        Stub implementation for sending an activation email.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.
        """
        return None

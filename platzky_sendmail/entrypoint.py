import smtplib
from typing_extensions import Annotated
from pydantic import BaseModel, Field, EmailStr, SecretStr, ValidationError
from typing import Any, Dict

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


def send_mail(
    sender_email, password, smtp_server, port, receiver_email, subject, message
):
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg.attach(MIMEText(message, "plain", "utf-8"))

    server = smtplib.SMTP_SSL(smtp_server, port)
    server.ehlo()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.close()


class SendMailConfig(BaseModel):
    """Configuration for email sending functionality."""

    user: EmailStr = Field(
        alias="sender_email", description="Email address to send from"
    )
    password: SecretStr = Field(
        alias="password", description="Password for authentication"
    )
    server: str = Field(
        alias="smtp_server", description="SMTP server hostname", min_length=1
    )
    port: Annotated[int, Field(strict=True, gt=0, lt=65536)] = Field(
        alias="port", description="SMTP server port"
    )
    receiver: EmailStr = Field(
        alias="receiver_email", description="Email address to send to"
    )
    subject: str = Field(alias="subject", description="Email subject", min_length=1)


def process(app: Any, config: Dict[str, Any]) -> Any:
    """Initialize the email notification plugin.

    Args:
        app: The application instance
        config: Plugin configuration dictionary

    Returns:
        The application instance

    Raises:
        ValidationError: If configuration is invalid
    """
    try:
        plugin_config = SendMailConfig.model_validate(config)
    except ValidationError as e:
        raise ValidationError(f"Invalid plugin configuration: {str(e)}")

    def notify(message):
        send_mail(
            sender_email=plugin_config.user,
            password=plugin_config.password.get_secret_value(),
            smtp_server=plugin_config.server,
            port=plugin_config.port,
            receiver_email=plugin_config.receiver,
            subject=plugin_config.subject,
            message=message,
        )

    app.add_notifier(notify)
    return app

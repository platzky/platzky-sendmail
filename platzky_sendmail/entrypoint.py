import smtplib

from pydantic import BaseModel, Field


def send_mail(sender_email, password, smtp_server, port, receiver_email, subject, message):
    full_message = f"From: {sender_email}\nTo: {receiver_email}\nSubject: {subject}\n\n{message}"
    server = smtplib.SMTP_SSL(smtp_server, port)
    server.ehlo()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, full_message)
    server.close()


from pydantic import EmailStr, SecretStr, conint

class SendMailConfig(BaseModel):
    """Configuration for email sending functionality."""
    user: EmailStr = Field(
        alias="sender_email",
        description="Email address to send from"
    )
    password: SecretStr = Field(
        alias="password",
        description="Password for authentication"
    )
    server: str = Field(
        alias="smtp_server",
        description="SMTP server hostname",
        min_length=1
    )
    port: conint(gt=0, lt=65536) = Field(
        alias="port",
        description="SMTP server port"
    )
    receiver: EmailStr = Field(
        alias="receiver_email",
        description="Email address to send to"
    )
    subject: str = Field(
        alias="subject",
        description="Email subject",
        min_length=1
    )


from typing import Any, Dict
from pydantic import ValidationError

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
        raise ValidationError(
            "Invalid plugin configuration",
            errors=e.errors()
        )

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

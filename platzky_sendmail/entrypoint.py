import smtplib
from typing_extensions import Annotated
from pydantic import Field, EmailStr, SecretStr

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from platzky.plugin.plugin import PluginBase, PluginBaseConfig


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


class SendMailConfig(PluginBaseConfig):
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


class SendMailPlugin(PluginBase[SendMailConfig]):
    """Email notification plugin for Platzky."""

    @classmethod
    def get_config_model(cls) -> type[SendMailConfig]:
        return SendMailConfig

    def process(self, app):
        """Initialize the email notification plugin.

        Args:
            app: The Platzky engine instance

        Returns:
            The engine instance with notifier added
        """
        config = self.config

        def notify(message):
            send_mail(
                sender_email=config.user,
                password=config.password.get_secret_value(),
                smtp_server=config.server,
                port=config.port,
                receiver_email=config.receiver,
                subject=config.subject,
                message=message,
            )

        app.add_notifier(notify)
        return app

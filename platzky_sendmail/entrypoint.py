import logging
import smtplib
from typing import Annotated, cast
from pydantic import Field, EmailStr, SecretStr

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders

from platzky.plugin.plugin import PluginBase, PluginBaseConfig
from platzky.attachment import AttachmentProtocol

logger = logging.getLogger("platzky.sendmail")


def send_mail(
    sender_email,
    password,
    smtp_server,
    port,
    receiver_email,
    subject,
    message,
    attachments: list[AttachmentProtocol] | None = None,
):
    """Send an email with optional attachments.

    Args:
        sender_email: Email address to send from
        password: Password for authentication
        smtp_server: SMTP server hostname
        port: SMTP server port
        receiver_email: Email address to send to
        subject: Email subject
        message: Email body text
        attachments: Optional list of Attachment objects
    """
    logger.info("Preparing email to %s with subject '%s'", receiver_email, subject)

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg.attach(MIMEText(message, "plain", "utf-8"))

    if attachments:
        logger.debug("Adding %d attachment(s)", len(attachments))
        for attachment in attachments:
            parts = attachment.mime_type.split("/", 1)
            if len(parts) != 2:
                logger.warning(
                    "Invalid MIME type '%s' for %s, defaulting to application/octet-stream",
                    attachment.mime_type,
                    attachment.filename,
                )
                maintype, subtype = "application", "octet-stream"
            else:
                maintype, subtype = parts
            part = MIMEBase(maintype, subtype)
            part.set_payload(attachment.content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment.filename,
            )
            msg.attach(part)
            logger.debug(
                "Attached file: %s (%s)", attachment.filename, attachment.mime_type
            )

    logger.debug("Connecting to SMTP server %s:%d", smtp_server, port)
    with smtplib.SMTP_SSL(smtp_server, port) as server:
        server.ehlo()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
    logger.info("Email sent successfully to %s", receiver_email)


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
        config = cast(SendMailConfig, self.config)
        logger.info(
            "Initializing SendMailPlugin: server=%s, sender=%s, receiver=%s",
            config.server,
            config.user,
            config.receiver,
        )

        def notify(
            message: str, attachments: list[AttachmentProtocol] | None = None
        ) -> None:
            """Send a notification email with optional attachments.

            Args:
                message: The email body text
                attachments: Optional list of Attachment objects
            """
            send_mail(
                sender_email=config.user,
                password=config.password.get_secret_value(),
                smtp_server=config.server,
                port=config.port,
                receiver_email=config.receiver,
                subject=config.subject,
                message=message,
                attachments=attachments,
            )

        app.add_notifier_with_attachments(notify)
        return app

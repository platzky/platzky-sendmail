"""Platzky plugin for sending emails with optional file attachments."""

import logging
import smtplib
from collections.abc import Sequence
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Annotated, Any

from platzky.attachment import Attachment
from platzky.notification_topics import NotificationTopic
from platzky.plugin.notifier import Notification, NotifierPluginBase
from pydantic import BaseModel, EmailStr, Field, SecretStr

logger = logging.getLogger("platzky.sendmail")

DEFAULT_MAX_TOTAL_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25MB


class AttachmentSizeError(Exception):
    """Raised when total attachment size exceeds the limit."""

    pass


def send_mail(
    sender_email: str,
    password: str,
    smtp_server: str,
    port: int,
    receiver_email: str,
    subject: str,
    message: str,
    attachments: Sequence[Attachment] | None = None,
    max_total_attachment_size: int = DEFAULT_MAX_TOTAL_ATTACHMENT_SIZE,
) -> None:
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
        max_total_attachment_size: Maximum total size of all attachments in bytes

    Raises:
        AttachmentSizeError: If total attachment size exceeds the limit
    """
    logger.info("Preparing email to %s with subject '%s'", receiver_email, subject)

    safe_subject = subject.replace("\r", "").replace("\n", " ")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = str(Header(safe_subject, "utf-8"))
    msg.attach(MIMEText(message, "plain", "utf-8"))

    if attachments:
        total_size = sum(len(attachment.content) for attachment in attachments)
        if total_size > max_total_attachment_size:
            raise AttachmentSizeError(
                f"Total attachment size ({total_size} bytes) exceeds limit "
                f"({max_total_attachment_size} bytes)"
            )
        logger.debug(
            "Adding %d attachment(s), total size: %d bytes",
            len(attachments),
            total_size,
        )
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
            logger.debug("Attached file: %s (%s)", attachment.filename, attachment.mime_type)

    logger.debug("Connecting to SMTP server %s:%d", smtp_server, port)
    try:
        if port == 465:
            logger.debug("Using SMTP_SSL (implicit TLS)")
            with smtplib.SMTP_SSL(smtp_server, port) as server:
                server.ehlo()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
        else:
            logger.debug("Using SMTP with STARTTLS")
            with smtplib.SMTP(smtp_server, port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
        logger.info("Email sent successfully to %s", receiver_email)
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", sender_email)
        raise
    except smtplib.SMTPException as e:
        logger.error("Failed to send email to %s: %s", receiver_email, e)
        raise


class SendMailConfig(BaseModel):
    """Configuration for email sending functionality."""

    user: EmailStr = Field(alias="sender_email", description="Email address to send from")
    password: SecretStr = Field(description="Password for authentication")
    server: str = Field(alias="smtp_server", description="SMTP server hostname", min_length=1)
    port: Annotated[int, Field(strict=True, gt=0, lt=65536)] = Field(description="SMTP server port")
    receiver: EmailStr = Field(alias="receiver_email", description="Email address to send to")
    subject: str = Field(description="Email subject", min_length=1)


class SendMailPlugin(NotifierPluginBase):
    """Email notification plugin for Platzky."""

    accepted_topics: frozenset[NotificationTopic] = frozenset({"security", "content", "general"})

    def __init__(self, config: dict[str, Any]) -> None:
        """Validate and store the plugin configuration.

        Args:
            config: Raw plugin configuration mapping (see ``SendMailConfig``).
        """
        super().__init__(config)
        self.config: SendMailConfig = SendMailConfig.model_validate(config)

    def notify(self, notification: Notification) -> None:
        """Send a notification email with optional attachments.

        Args:
            notification: The notification payload to deliver.
        """
        config = self.config
        logger.info(
            "SendMailPlugin handling topic=%s: server=%s, sender=%s, receiver=%s",
            notification.topic,
            config.server,
            config.user,
            config.receiver,
        )
        send_mail(
            sender_email=config.user,
            password=config.password.get_secret_value(),
            smtp_server=config.server,
            port=config.port,
            receiver_email=config.receiver,
            subject=config.subject,
            message=notification.message,
            attachments=list(notification.attachments),
        )

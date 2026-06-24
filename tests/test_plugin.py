import base64
import ssl
from typing import TypedDict
from unittest.mock import MagicMock, patch

import pytest
from platzky.attachment import Attachment
from platzky.plugin.notifier import Notification, NotifierPluginBase

from platzky_sendmail.plugin import (
    DEFAULT_SMTP_TIMEOUT,
    AttachmentSizeError,
    SendMailPlugin,
    send_mail,
)


class MailConfig(TypedDict):
    sender_email: str
    password: str
    smtp_server: str
    port: int
    receiver_email: str
    subject: str


@pytest.fixture
def valid_config() -> MailConfig:
    return MailConfig(
        sender_email="test@example.com",
        password="password",
        smtp_server="smtp.example.com",
        port=465,
        receiver_email="receiver@example.com",
        subject="Test Subject",
    )


def test_that_sends_email_successfully(valid_config: MailConfig) -> None:
    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
        )

        mock_server.login.assert_called_once_with(
            valid_config["sender_email"], valid_config["password"]
        )
        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        assert "Content-Type: multipart/mixed" in sent_message
        assert "From: test@example.com" in sent_message
        assert "To: receiver@example.com" in sent_message
        assert "Subject: Test Subject" in sent_message
        # Decode the base64 content
        start = sent_message.find("VGVzdCBNZXNzYWdl")
        end = sent_message.find("\n\n--", start)
        decoded_message = base64.b64decode(sent_message[start:end]).decode("utf-8")
        assert "Test Message" in decoded_message


def test_that_raises_exception_on_invalid_smtp_server(valid_config: MailConfig) -> None:
    with patch("smtplib.SMTP_SSL", side_effect=Exception("Invalid SMTP server")):
        with pytest.raises(Exception, match="Invalid SMTP server"):
            send_mail(
                sender_email=valid_config["sender_email"],
                password=valid_config["password"],
                smtp_server="invalid.smtp.server",
                port=valid_config["port"],
                receiver_email=valid_config["receiver_email"],
                subject=valid_config["subject"],
                message="Test Message",
            )


def test_plugin_is_notifier_plugin_base(valid_config: MailConfig) -> None:
    plugin = SendMailPlugin(dict(valid_config))
    assert isinstance(plugin, NotifierPluginBase)


def test_plugin_declares_accepted_topics(valid_config: MailConfig) -> None:
    plugin = SendMailPlugin(dict(valid_config))
    assert "general" in plugin.accepted_topics


def test_notify_sends_email(valid_config: MailConfig) -> None:
    plugin = SendMailPlugin(dict(valid_config))

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        plugin.notify(Notification(message="Test Message", topic="general"))

        mock_server.login.assert_called_once_with(
            valid_config["sender_email"], valid_config["password"]
        )
        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        assert "Content-Type: multipart/mixed" in sent_message
        assert "From: test@example.com" in sent_message
        assert "To: receiver@example.com" in sent_message
        assert "Subject: Test Subject" in sent_message
        start = sent_message.find("VGVzdCBNZXNzYWdl")
        end = sent_message.find("\n\n--", start)
        decoded_message = base64.b64decode(sent_message[start:end]).decode("utf-8")
        assert "Test Message" in decoded_message


def test_send_mail_with_attachment(valid_config: MailConfig) -> None:
    attachment = Attachment("test.txt", b"Hello, World!", "text/plain")

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
            attachments=[attachment],
        )

        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        assert 'filename="test.txt"' in sent_message
        assert "Content-Type: text/plain" in sent_message


def test_notify_sends_email_with_attachment(valid_config: MailConfig) -> None:
    attachment = Attachment("report.pdf", b"%PDF-1.4", "application/pdf")

    plugin = SendMailPlugin(dict(valid_config))

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        plugin.notify(
            Notification(
                message="Test Message",
                topic="general",
                attachments=frozenset({attachment}),
            )
        )

        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        assert 'filename="report.pdf"' in sent_message
        assert "Content-Type: application/pdf" in sent_message


def test_send_mail_with_invalid_mime_type_falls_back_to_octet_stream(
    valid_config: MailConfig,
) -> None:
    """Test that invalid MIME types fall back to application/octet-stream."""
    attachment = Attachment("test.bin", b"binary data", "invalid-mime-type")  # No slash

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
            attachments=[attachment],
        )

        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        assert 'filename="test.bin"' in sent_message
        assert "Content-Type: application/octet-stream" in sent_message


def test_subject_header_injection_is_prevented(valid_config: MailConfig) -> None:
    """Test that newlines in subject are sanitized to prevent header injection."""
    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject="Legit Subject\nBcc: attacker@evil.com",
            message="Test Message",
        )

        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        headers = sent_message.split("\n\n")[0]
        # Newline replaced with space - "Bcc:" is now part of Subject, not a separate header
        assert "\nBcc:" not in headers  # No separate Bcc header line
        assert "Subject: Legit Subject Bcc: attacker@evil.com" in headers


def test_send_mail_uses_starttls_on_port_587(valid_config: MailConfig) -> None:
    """Test that port 587 uses SMTP with STARTTLS instead of SMTP_SSL."""
    with patch("platzky_sendmail.plugin.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=587,  # STARTTLS port
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
        )

        # Verify SMTP (not SMTP_SSL) was used, with an explicit timeout
        mock_smtp.assert_called_once_with(
            valid_config["smtp_server"], 587, timeout=DEFAULT_SMTP_TIMEOUT
        )
        # Verify STARTTLS was called with an explicit TLS context
        mock_server.starttls.assert_called_once()
        assert isinstance(mock_server.starttls.call_args.kwargs["context"], ssl.SSLContext)
        # Verify login and send
        mock_server.login.assert_called_once_with(
            valid_config["sender_email"], valid_config["password"]
        )
        mock_server.sendmail.assert_called_once()


def test_send_mail_uses_ssl_on_port_465(valid_config: MailConfig) -> None:
    """Test that port 465 uses SMTP_SSL (implicit TLS)."""
    with patch("platzky_sendmail.plugin.smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=465,  # SSL port
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
        )

        # Verify SMTP_SSL was used with an explicit timeout and TLS context
        mock_smtp_ssl.assert_called_once()
        args = mock_smtp_ssl.call_args
        assert args.args == (valid_config["smtp_server"], 465)
        assert args.kwargs["timeout"] == DEFAULT_SMTP_TIMEOUT
        assert isinstance(args.kwargs["context"], ssl.SSLContext)
        # Verify login and send (no starttls call)
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()


def test_attachment_size_limit_exceeded_raises_error(valid_config: MailConfig) -> None:
    """Test that exceeding attachment size limit raises AttachmentSizeError."""
    attachment = Attachment("large_file.bin", b"x" * 1000, "application/octet-stream")

    with pytest.raises(AttachmentSizeError, match="exceeds limit"):
        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
            attachments=[attachment],
            max_total_attachment_size=500,  # 500 bytes limit
        )


def test_attachment_within_size_limit_succeeds(valid_config: MailConfig) -> None:
    """Test that attachments within size limit are sent successfully."""
    attachment = Attachment("small_file.bin", b"x" * 100, "application/octet-stream")

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
            attachments=[attachment],
            max_total_attachment_size=500,  # 500 bytes limit
        )

        mock_server.sendmail.assert_called_once()


def test_multiple_attachments_total_size_limit(valid_config: MailConfig) -> None:
    """Test that total size of multiple attachments is checked."""
    attachment1 = Attachment("file1.bin", b"x" * 300, "application/octet-stream")
    attachment2 = Attachment("file2.bin", b"y" * 300, "application/octet-stream")

    # Total: 600 bytes, limit: 500 bytes
    with pytest.raises(AttachmentSizeError, match=r"600 bytes.*exceeds limit.*500 bytes"):
        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message",
            attachments=[attachment1, attachment2],
            max_total_attachment_size=500,
        )

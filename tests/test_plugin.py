import pytest
from unittest.mock import patch, MagicMock
from platzky_sendmail.entrypoint import send_mail, SendMailPlugin
from platzky.attachment import create_attachment_class
from platzky.config import AttachmentConfig
import base64


@pytest.fixture
def valid_config():
    return {
        "sender_email": "test@example.com",
        "password": "password",
        "smtp_server": "smtp.example.com",
        "port": 465,
        "receiver_email": "receiver@example.com",
        "subject": "Test Subject",
    }


def test_that_sends_email_successfully(valid_config):
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


def test_that_raises_exception_on_invalid_smtp_server(valid_config):
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


def test_process_adds_notifier_to_app(valid_config):
    app = MagicMock()
    config = valid_config

    plugin = SendMailPlugin(config)
    plugin.process(app)

    app.add_notifier_with_attachments.assert_called_once()
    notifier = app.add_notifier_with_attachments.call_args[0][0]
    assert callable(notifier)


def test_notifier_sends_email(valid_config):
    app = MagicMock()
    config = valid_config

    plugin = SendMailPlugin(config)
    plugin.process(app)
    notifier = app.add_notifier_with_attachments.call_args[0][0]

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notifier("Test Message")

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


def test_send_mail_with_attachment(valid_config):
    config = AttachmentConfig(
        allowed_mime_types=frozenset({"text/plain"}),
        allowed_extensions=frozenset({"txt"}),
    )
    Attachment = create_attachment_class(config)
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


def test_notifier_sends_email_with_attachment(valid_config):
    config = AttachmentConfig()
    Attachment = create_attachment_class(config)
    attachment = Attachment("report.pdf", b"%PDF-1.4", "application/pdf")

    app = MagicMock()
    plugin = SendMailPlugin(valid_config)
    plugin.process(app)
    notifier = app.add_notifier_with_attachments.call_args[0][0]

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notifier("Test Message", attachments=[attachment])

        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args[0][2]
        assert 'filename="report.pdf"' in sent_message
        assert "Content-Type: application/pdf" in sent_message

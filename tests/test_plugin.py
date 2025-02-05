import pytest
from unittest.mock import patch, MagicMock
from platzky_sendmail.entrypoint import send_mail, process, SendMailConfig

@pytest.fixture
def valid_config():
    return {
        "sender_email": "test@example.com",
        "password": "password",
        "smtp_server": "smtp.example.com",
        "port": 465,
        "receiver_email": "receiver@example.com",
        "subject": "Test Subject"
    }

def test_that_sends_email_successfully(valid_config):
    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        send_mail(
            sender_email=valid_config["sender_email"],
            password=valid_config["password"],
            smtp_server=valid_config["smtp_server"],
            port=valid_config["port"],
            receiver_email=valid_config["receiver_email"],
            subject=valid_config["subject"],
            message="Test Message"
        )

        mock_server.login.assert_called_once_with(valid_config["sender_email"], valid_config["password"])
        mock_server.sendmail.assert_called_once_with(
            valid_config["sender_email"],
            valid_config["receiver_email"],
            f"From: {valid_config['sender_email']}\nTo: {valid_config['receiver_email']}\nSubject: {valid_config['subject']}\n\nTest Message"
        )
        mock_server.close.assert_called_once()

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
                message="Test Message"
            )

def test_process_adds_notifier_to_app(valid_config):
    app = MagicMock()
    config = valid_config

    process(app, config)

    app.add_notifier.assert_called_once()
    notifier = app.add_notifier.call_args[0][0]
    assert callable(notifier)

def test_notifier_sends_email(valid_config):
    app = MagicMock()
    config = valid_config

    process(app, config)
    notifier = app.add_notifier.call_args[0][0]

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        notifier("Test Message")

        mock_server.login.assert_called_once_with(valid_config["sender_email"], valid_config["password"])
        mock_server.sendmail.assert_called_once_with(
            valid_config["sender_email"],
            valid_config["receiver_email"],
            f"From: {valid_config['sender_email']}\nTo: {valid_config['receiver_email']}\nSubject: {valid_config['subject']}\n\nTest Message"
        )
        mock_server.close.assert_called_once()

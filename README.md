# platzky-sendmail

Platzky plugin for sending emails with optional file attachments.

## Installation

```sh
pip install platzky-sendmail
```

## Activation

Add the plugin to the `plugins` list in your Platzky database configuration.
The `name` must match the entry-point key declared in `pyproject.toml`:

```json
{
    "plugins": [
        {
            "name": "sendmail",
            "config": {
                "sender_email": "sender@example.com",
                "password": "MY-SECRET-PASSWORD",
                "smtp_server": "smtp.example.com",
                "port": 465,
                "receiver_email": "receiver@example.com",
                "subject": "Default email subject"
            }
        }
    ]
}
```

Port `465` uses implicit SSL (`SMTP_SSL`); any other port uses explicit TLS via
`STARTTLS`.

## Development

This plugin extends [`NotifierPluginBase`](https://platzky.readthedocs.io/en/latest/plugins.html).
It declares the notification topics it accepts via `accepted_topics` and
implements `notify(self, notification)` to deliver the message — and any
attachments — over SMTP. Total attachment size is capped at 25 MB
(`DEFAULT_MAX_TOTAL_ATTACHMENT_SIZE`), raising `AttachmentSizeError` if exceeded.

```sh
poetry install        # Install dependencies
make lint             # Auto-format and fix (black + ruff --fix)
make lint-check       # Check formatting/linting + types + docstrings (CI)
make dev              # Lint + type check (pyright)
make unit-tests       # Run all tests
make coverage         # Tests with coverage
make build            # Build wheel/sdist
```

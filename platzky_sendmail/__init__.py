from platzky_sendmail.plugin import (
    DEFAULT_MAX_TOTAL_ATTACHMENT_SIZE,
    AttachmentSizeError,
    SendMailPlugin,
)

Plugin = SendMailPlugin

__all__ = [
    "DEFAULT_MAX_TOTAL_ATTACHMENT_SIZE",
    "AttachmentSizeError",
    "Plugin",
    "SendMailPlugin",
]

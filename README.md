# Platzky Sendmail Plugin

## Overview

Platzky Sendmail is a plugin for snding mails

## Installation

```sh
pip install platzky-sendmail
```

### Usage

```json
"plugins": [
{
            "name": "sendmail",
            "config": {
                "port": 465,
                "smtp_server": "smtp.example.com",
                "receiver_email": "receiver@example.com",
                "password": "MY-SECRET-PASSWORD",
                "sender_email": "sender@example.com",
                "subject": "Default email subject"
}
]



```

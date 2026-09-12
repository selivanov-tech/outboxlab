import base64
from email import message_from_bytes
from email.policy import default

from app.contexts.messaging.infrastructure.gmail.sender import build_raw_message


def test_build_raw_message_sets_headers_and_body() -> None:
    raw = build_raw_message(
        mailbox_email="ops@example.com",
        to_email="lead@example.com",
        subject="Hello",
        body="Hi there",
        rfc822_message_id="<abc@example.com>",
    )

    decoded = base64.urlsafe_b64decode(raw)
    message = message_from_bytes(decoded, policy=default)

    assert message["From"] == "ops@example.com"
    assert message["To"] == "lead@example.com"
    assert message["Subject"] == "Hello"
    assert message["Message-ID"] == "<abc@example.com>"
    assert "Hi there" in message.get_content()

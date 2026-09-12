import base64
from email.message import EmailMessage

import httpx

from app.contexts.messaging.application.ports.email_sender import SentEmail
from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)

_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def build_raw_message(
    *,
    mailbox_email: str,
    to_email: str,
    subject: str,
    body: str,
    rfc822_message_id: str,
) -> str:
    message = EmailMessage()
    message["From"] = mailbox_email
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = rfc822_message_id
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


class GmailApiSender:
    def __init__(
        self,
        client: httpx.AsyncClient,
        token_provider: GoogleAccessTokenProvider,
    ) -> None:
        self._client = client
        self._token_provider = token_provider

    async def send(
        self,
        *,
        mailbox_email: str,
        to_email: str,
        subject: str,
        body: str,
        rfc822_message_id: str,
    ) -> SentEmail:
        raw = build_raw_message(
            mailbox_email=mailbox_email,
            to_email=to_email,
            subject=subject,
            body=body,
            rfc822_message_id=rfc822_message_id,
        )
        token = await self._token_provider.token()
        response = await self._client.post(
            _SEND_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"raw": raw},
        )
        response.raise_for_status()
        data = response.json()
        return SentEmail(
            provider_message_id=data["id"],
            provider_thread_id=data["threadId"],
        )

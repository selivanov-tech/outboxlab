from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SentEmail:
    provider_message_id: str
    provider_thread_id: str


class EmailSenderPort(Protocol):
    async def send(
        self,
        *,
        mailbox_email: str,
        to_email: str,
        subject: str,
        body: str,
        rfc822_message_id: str,
    ) -> SentEmail: ...

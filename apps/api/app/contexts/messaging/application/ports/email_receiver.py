from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class FetchedMessage:
    provider_message_id: str
    provider_thread_id: str
    from_email: str
    subject: str
    snippet: str
    in_reply_to_header: str | None
    references_header: str | None
    received_at: datetime
    body_text: str = ""
    is_bounce: bool = False


@dataclass(frozen=True)
class FetchResult:
    new_cursor: str
    messages: tuple[FetchedMessage, ...]


class EmailReceiverPort(Protocol):
    async def fetch_new(
        self, *, mailbox_email: str, since_cursor: str | None
    ) -> FetchResult: ...

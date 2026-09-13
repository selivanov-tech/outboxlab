from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DispatchSent:
    outbound_message_id: UUID
    sent_at: datetime


@dataclass(frozen=True)
class DispatchDeferred:
    retry_at: datetime
    reason: str


@dataclass(frozen=True)
class DispatchSuppressed:
    pass


@dataclass(frozen=True)
class DispatchFailed:
    error: str


DispatchResult = DispatchSent | DispatchDeferred | DispatchSuppressed | DispatchFailed


class EmailDispatchPort(Protocol):
    async def dispatch(
        self, *, workspace_id: UUID, to_email: str, subject: str, body: str
    ) -> DispatchResult: ...

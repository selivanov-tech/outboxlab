from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.contexts.campaign.domain.lead import Lead, LeadState


@dataclass(frozen=True)
class LeadStats:
    leads: int
    contacted: int
    emails_sent: int
    bounced: int
    in_progress: int
    completed: int
    reply_intents: dict[str, int]


class LeadRepositoryPort(Protocol):
    async def add_many(self, leads: Sequence[Lead]) -> None: ...

    async def get(self, lead_id: UUID) -> Lead | None: ...

    async def list_by_campaign(self, campaign_id: UUID) -> list[Lead]: ...

    async def list_pending(self, campaign_id: UUID) -> list[Lead]: ...

    async def emails(self, campaign_id: UUID) -> set[str]: ...

    async def update_many(self, leads: Sequence[Lead]) -> None: ...

    async def count_by_state(
        self, campaign_ids: Sequence[UUID]
    ) -> dict[UUID, dict[LeadState, int]]: ...

    async def stats(self, campaign_id: UUID) -> LeadStats: ...

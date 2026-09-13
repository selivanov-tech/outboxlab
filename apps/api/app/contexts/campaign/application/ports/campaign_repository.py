from typing import Protocol
from uuid import UUID

from app.contexts.campaign.domain.campaign import Campaign


class CampaignRepositoryPort(Protocol):
    async def add(self, campaign: Campaign) -> None: ...

    async def get(self, campaign_id: UUID) -> Campaign | None: ...

    async def list(self) -> list[Campaign]: ...

    async def update_status(self, campaign: Campaign) -> None: ...

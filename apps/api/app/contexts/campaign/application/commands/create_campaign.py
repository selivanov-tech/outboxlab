from dataclasses import dataclass
from uuid import UUID

from app.contexts.campaign.application.errors import MailboxNotConnectedError
from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.mailbox_lookup import MailboxLookupPort
from app.contexts.campaign.domain.campaign import Campaign, StepDraft


@dataclass(frozen=True)
class CreateCampaignCommand:
    name: str
    steps: tuple[StepDraft, ...]


class CreateCampaignHandler:
    def __init__(
        self, mailboxes: MailboxLookupPort, campaigns: CampaignRepositoryPort
    ) -> None:
        self._mailboxes = mailboxes
        self._campaigns = campaigns

    async def execute(
        self, command: CreateCampaignCommand, workspace_id: UUID
    ) -> Campaign:
        mailbox_id = await self._mailboxes.mailbox_id_for(workspace_id)
        if mailbox_id is None:
            raise MailboxNotConnectedError
        campaign = Campaign.new(
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            name=command.name,
            steps=command.steps,
        )
        await self._campaigns.add(campaign)
        return campaign

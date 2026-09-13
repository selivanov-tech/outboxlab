from datetime import datetime
from uuid import UUID

from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.classified_reply_feed import (
    ClassifiedReply,
    ClassifiedReplyFeedPort,
)
from app.contexts.campaign.application.ports.lead_repository import LeadRepositoryPort
from app.contexts.campaign.application.ports.send_job_repository import (
    SendJobRepositoryPort,
)
from app.contexts.campaign.domain.errors import LeadTransitionError
from app.contexts.campaign.domain.lead import Lead


class HandleClassifiedRepliesHandler:
    def __init__(
        self,
        feed: ClassifiedReplyFeedPort,
        campaigns: CampaignRepositoryPort,
        leads: LeadRepositoryPort,
        jobs: SendJobRepositoryPort,
    ) -> None:
        self._feed = feed
        self._campaigns = campaigns
        self._leads = leads
        self._jobs = jobs

    async def run_once(
        self, *, workspace_id: UUID, limit: int, moment: datetime
    ) -> list[Lead]:
        stopped: list[Lead] = []
        for reply in await self._feed.claim(workspace_id=workspace_id, limit=limit):
            lead = await self._stop_lead(reply, moment)
            if lead is not None:
                stopped.append(lead)
            await self._feed.acknowledge(reply, moment)
        return stopped

    async def _stop_lead(self, reply: ClassifiedReply, moment: datetime) -> Lead | None:
        if reply.matched_outbound_id is None:
            return None
        lead_id = await self._jobs.find_lead_id_by_outbound_message(
            reply.matched_outbound_id
        )
        lead = await self._leads.get(lead_id) if lead_id is not None else None
        if lead is None:
            return None
        campaign = await self._campaigns.get(lead.campaign_id)
        if campaign is None:
            return None
        try:
            stopped = campaign.stop_on_reply(lead, reply.intent, moment)
        except LeadTransitionError:
            return None
        if stopped is lead:
            return None
        await self._leads.update_many([stopped])
        await self._jobs.cancel_pending_for_lead(lead.id, moment)
        return stopped

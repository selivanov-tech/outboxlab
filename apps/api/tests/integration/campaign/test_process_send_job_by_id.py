from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.process_send_jobs import (
    ClaimDueSendJobsHandler,
    ProcessClaimedSendJobHandler,
    ProcessSendJobByIdHandler,
    SendJobNotClaimedError,
    SendJobOutcome,
)
from app.contexts.campaign.infrastructure.messaging.email_dispatch import (
    MessagingEmailDispatch,
)
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import Tenant, seed_tenant
from tests.integration.campaign.scenarios import start_campaign
from tests.integration.campaign.test_process_send_jobs import FakeGmailSender


def _handler(
    session: AsyncSession, sender: FakeGmailSender
) -> ProcessSendJobByIdHandler:
    jobs = SendJobRepository(session)
    return ProcessSendJobByIdHandler(
        jobs,
        ProcessClaimedSendJobHandler(
            CampaignRepository(session),
            LeadRepository(session),
            jobs,
            MessagingEmailDispatch(session, sender),
        ),
    )


async def _claim(session: AsyncSession, tenant: Tenant):
    return await ClaimDueSendJobsHandler(SendJobRepository(session)).execute(
        workspace_id=tenant.workspace_id,
        worker_id="go-test",
        limit=10,
        moment=now() + timedelta(seconds=1),
    )


async def test_a_job_claimed_elsewhere_is_processed_once(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    await start_campaign(session, tenant, ["lead@example.com"])
    (job,) = await _claim(session, tenant)
    sender = FakeGmailSender()
    handler = _handler(session, sender)

    outcome = await handler.execute(
        job_id=job.id, workspace_id=tenant.workspace_id, moment=now()
    )

    assert outcome is SendJobOutcome.SENT
    assert sender.sent == [("lead@example.com", "Hello")]
    with pytest.raises(SendJobNotClaimedError):
        await handler.execute(
            job_id=job.id, workspace_id=tenant.workspace_id, moment=now()
        )
    assert len(sender.sent) == 1


async def test_an_unclaimed_job_or_another_workspace_is_rejected(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session, "owner")
    other = await seed_tenant(session, "other")
    await start_campaign(session, tenant, ["lead@example.com"])
    handler = _handler(session, FakeGmailSender())
    (claimed,) = await _claim(session, tenant)

    with pytest.raises(SendJobNotClaimedError):
        await handler.execute(
            job_id=claimed.id, workspace_id=other.workspace_id, moment=now()
        )

    await start_campaign(session, tenant, ["pending@example.com"])
    pending_ids = {job.id for job in await _claim(session, tenant)}
    assert claimed.id not in pending_ids

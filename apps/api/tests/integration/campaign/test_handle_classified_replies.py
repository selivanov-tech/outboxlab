import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.handle_classified_replies import (
    HandleClassifiedRepliesHandler,
)
from app.contexts.campaign.domain.lead import LeadState, StopReason
from app.contexts.campaign.domain.send_job import SendJobStatus
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.campaign.infrastructure.messaging.reply_feed import (
    ClassifiedReplyFeed,
)
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.contexts.messaging.infrastructure.persistence.outbox_writer import (
    OutboxEventWriter,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import Tenant, seed_tenant
from tests.integration.campaign.scenarios import start_campaign
from tests.integration.campaign.test_process_send_jobs import (
    FakeGmailSender,
    process_due,
)


def _handler(session: AsyncSession) -> HandleClassifiedRepliesHandler:
    return HandleClassifiedRepliesHandler(
        ClassifiedReplyFeed(session),
        CampaignRepository(session),
        LeadRepository(session),
        SendJobRepository(session),
    )


async def _sent_step_one(
    session: AsyncSession, tenant: Tenant
) -> tuple[uuid.UUID, uuid.UUID]:
    _, (lead,) = await start_campaign(session, tenant, ["lead@example.com"])
    await process_due(session, tenant, FakeGmailSender(), now() + timedelta(seconds=1))
    outbound_id = (
        await session.execute(
            select(SendJobRow.outbound_message_id).where(
                SendJobRow.lead_id == lead.id,
                SendJobRow.status == SendJobStatus.DONE.value,
            )
        )
    ).scalar_one()
    assert outbound_id is not None
    return lead.id, outbound_id


async def _record_reply(
    session: AsyncSession,
    tenant: Tenant,
    intent: str,
    matched_outbound_id: uuid.UUID | None,
    *,
    version: int = 2,
) -> None:
    payload: dict[str, object] = {
        "workspace_id": tenant.workspace_id,
        "inbound_id": uuid.uuid7(),
        "intent": intent,
    }
    if version == 2:
        payload |= {"event_version": 2, "matched_outbound_id": matched_outbound_id}
    await OutboxEventWriter(session).record(
        "ReplyClassified", tenant.workspace_id, uuid.uuid7(), payload
    )


async def _statuses(session: AsyncSession, lead_id: uuid.UUID) -> list[str]:
    stmt = (
        select(SendJobRow.status)
        .where(SendJobRow.lead_id == lead_id)
        .order_by(SendJobRow.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def test_reply_pauses_the_lead_and_cancels_the_follow_up(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    lead_id, outbound_id = await _sent_step_one(session, tenant)
    await _record_reply(session, tenant, "positive", outbound_id)

    stopped = await _handler(session).run_once(
        workspace_id=tenant.workspace_id, limit=10, moment=now()
    )

    assert [lead.id for lead in stopped] == [lead_id]
    lead = await LeadRepository(session).get(lead_id)
    assert lead is not None
    assert (lead.state, lead.stop_reason, lead.reply_intent) == (
        LeadState.PAUSED,
        StopReason.REPLIED,
        "positive",
    )
    assert await _statuses(session, lead_id) == [
        SendJobStatus.DONE.value,
        SendJobStatus.CANCELLED.value,
    ]


async def test_an_event_is_handled_only_once(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    _, outbound_id = await _sent_step_one(session, tenant)
    await _record_reply(session, tenant, "positive", outbound_id)
    handler = _handler(session)
    await handler.run_once(workspace_id=tenant.workspace_id, limit=10, moment=now())

    again = await handler.run_once(
        workspace_id=tenant.workspace_id, limit=10, moment=now()
    )

    assert again == []


async def test_bounce_fails_the_lead(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    lead_id, outbound_id = await _sent_step_one(session, tenant)
    await _record_reply(session, tenant, "bounce", outbound_id)

    await _handler(session).run_once(
        workspace_id=tenant.workspace_id, limit=10, moment=now()
    )

    lead = await LeadRepository(session).get(lead_id)
    assert lead is not None
    assert (lead.state, lead.stop_reason) == (LeadState.FAILED, StopReason.BOUNCED)
    assert SendJobStatus.PENDING.value not in await _statuses(session, lead_id)


async def test_v1_events_and_test_email_replies_are_acknowledged_without_changes(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    lead_id, outbound_id = await _sent_step_one(session, tenant)
    await _record_reply(session, tenant, "positive", outbound_id, version=1)
    await _record_reply(session, tenant, "positive", uuid.uuid7())
    handler = _handler(session)

    stopped = await handler.run_once(
        workspace_id=tenant.workspace_id, limit=10, moment=now()
    )

    assert stopped == []
    lead = await LeadRepository(session).get(lead_id)
    assert lead is not None
    assert lead.state is LeadState.SENT
    assert (
        await ClassifiedReplyFeed(session).claim(
            workspace_id=tenant.workspace_id, limit=10
        )
        == []
    )


async def test_events_of_other_workspaces_are_not_claimed(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session, "owner")
    other = await seed_tenant(session, "other")
    await _record_reply(session, tenant, "positive", uuid.uuid7())

    assert (
        await ClassifiedReplyFeed(session).claim(
            workspace_id=other.workspace_id, limit=10
        )
        == []
    )

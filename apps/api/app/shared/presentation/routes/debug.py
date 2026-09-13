from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contexts.campaign.infrastructure.db.models import Lead as LeadRow
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.identity.infrastructure.db.models import Workspace as WorkspaceRow
from app.contexts.mailbox.infrastructure.db.models import Mailbox as MailboxRow
from app.contexts.messaging.infrastructure.db.models import (
    InboundMessage as InboundMessageRow,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboundMessage as OutboundMessageRow,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboxEvent as OutboxEventRow,
)
from app.shared.infrastructure.db.engine import get_session_factory

router = APIRouter()


async def _session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        workspace_id = get_settings().mailbox_workspace_id
        if workspace_id:
            await session.execute(
                text("SELECT set_config('app.workspace_id', :ws, true)"),
                {"ws": workspace_id},
            )
        yield session


@router.get("/debug/state")
async def state(
    session: Annotated[AsyncSession, Depends(_session)],
) -> dict[str, object]:
    try:
        workspace_count = (
            await session.execute(select(func.count()).select_from(WorkspaceRow))
        ).scalar_one()
        outbound_count = (
            await session.execute(select(func.count()).select_from(OutboundMessageRow))
        ).scalar_one()
        inbound_count = (
            await session.execute(select(func.count()).select_from(InboundMessageRow))
        ).scalar_one()
        last_sync_cursor = (
            await session.execute(
                select(MailboxRow.last_sync_cursor)
                .order_by(MailboxRow.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        intent_rows = (
            await session.execute(
                select(InboundMessageRow.intent, func.count())
                .where(InboundMessageRow.intent.is_not(None))
                .group_by(InboundMessageRow.intent)
            )
        ).all()
        lead_state_rows = (
            await session.execute(
                select(LeadRow.state, func.count()).group_by(LeadRow.state)
            )
        ).all()
        send_job_rows = (
            await session.execute(
                select(SendJobRow.status, func.count()).group_by(SendJobRow.status)
            )
        ).all()
        event_rows = (
            await session.execute(
                select(
                    OutboxEventRow.event_type,
                    OutboxEventRow.aggregate_id,
                    OutboxEventRow.created_at,
                )
                .order_by(OutboxEventRow.created_at.desc(), OutboxEventRow.id.desc())
                .limit(10)
            )
        ).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"db: {exc.__class__.__name__}")

    return {
        "db": "ok",
        "workspace_count": int(workspace_count),
        "mailbox_last_sync_cursor": last_sync_cursor,
        "outbound_count": int(outbound_count),
        "inbound_count": int(inbound_count),
        "intents": {intent: int(count) for intent, count in intent_rows},
        "leads": {state: int(count) for state, count in lead_state_rows},
        "send_jobs": {status: int(count) for status, count in send_job_rows},
        "recent_events": [
            {
                "event_type": event_type,
                "aggregate_id": str(aggregate_id),
                "created_at": created_at.isoformat(),
            }
            for event_type, aggregate_id, created_at in event_rows
        ],
    }

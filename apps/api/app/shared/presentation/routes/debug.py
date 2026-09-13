from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.infrastructure.db.models import Lead as LeadRow
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
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
from app.shared.infrastructure.db.session import get_session
from app.shared.presentation.dependencies import require_workspace

router = APIRouter()


async def _count(session: AsyncSession, stmt) -> int:
    return int((await session.execute(stmt)).scalar_one())


async def _grouped(session: AsyncSession, stmt) -> dict[str, int]:
    return {key: int(count) for key, count in (await session.execute(stmt)).all()}


@router.get("/debug/state")
async def state(
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    try:
        outbound_count = await _count(
            session,
            select(func.count())
            .select_from(OutboundMessageRow)
            .where(OutboundMessageRow.workspace_id == workspace_id),
        )
        inbound_count = await _count(
            session,
            select(func.count())
            .select_from(InboundMessageRow)
            .where(InboundMessageRow.workspace_id == workspace_id),
        )
        last_sync_cursor = (
            await session.execute(
                select(MailboxRow.last_sync_cursor)
                .where(MailboxRow.workspace_id == workspace_id)
                .order_by(MailboxRow.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        intents = await _grouped(
            session,
            select(InboundMessageRow.intent, func.count())
            .where(
                InboundMessageRow.workspace_id == workspace_id,
                InboundMessageRow.intent.is_not(None),
            )
            .group_by(InboundMessageRow.intent),
        )
        leads = await _grouped(
            session,
            select(LeadRow.state, func.count())
            .where(LeadRow.workspace_id == workspace_id)
            .group_by(LeadRow.state),
        )
        send_jobs = await _grouped(
            session,
            select(SendJobRow.status, func.count())
            .where(SendJobRow.workspace_id == workspace_id)
            .group_by(SendJobRow.status),
        )
        event_rows = (
            await session.execute(
                select(
                    OutboxEventRow.event_type,
                    OutboxEventRow.aggregate_id,
                    OutboxEventRow.created_at,
                )
                .where(OutboxEventRow.workspace_id == workspace_id)
                .order_by(OutboxEventRow.created_at.desc(), OutboxEventRow.id.desc())
                .limit(10)
            )
        ).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"db: {exc.__class__.__name__}")

    return {
        "db": "ok",
        "workspace_id": str(workspace_id),
        "mailbox_last_sync_cursor": last_sync_cursor,
        "outbound_count": outbound_count,
        "inbound_count": inbound_count,
        "intents": intents,
        "leads": leads,
        "send_jobs": send_jobs,
        "recent_events": [
            {
                "event_type": event_type,
                "aggregate_id": str(aggregate_id),
                "created_at": created_at.isoformat(),
            }
            for event_type, aggregate_id, created_at in event_rows
        ],
    }

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboxEvent as OutboxEventRow,
)
from app.contexts.messaging.infrastructure.persistence.outbox_writer import (
    OutboxEventWriter,
)
from app.shared.util.clock import now


async def test_record_stamps_event_type_and_json_normalizes(
    session: AsyncSession,
) -> None:
    ws = Workspace.new("acme")
    await WorkspaceRepository(session).add(ws)

    aggregate_id = uuid.uuid7()
    received_at = now()
    await OutboxEventWriter(session).record(
        "InboundReceived",
        ws.id,
        aggregate_id,
        {"inbound_id": aggregate_id, "received_at": received_at},
    )

    row = (
        (
            await session.execute(
                select(OutboxEventRow).where(OutboxEventRow.workspace_id == ws.id)
            )
        )
        .scalars()
        .one()
    )
    assert row.event_type == "InboundReceived"
    assert row.aggregate_id == aggregate_id
    assert row.payload["event_type"] == "InboundReceived"
    assert row.payload["inbound_id"] == str(aggregate_id)
    assert row.payload["received_at"] == received_at.isoformat()

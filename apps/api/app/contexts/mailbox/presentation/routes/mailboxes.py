from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.mailbox.application.queries.list_mailboxes import (
    ListMailboxesHandler,
)
from app.contexts.mailbox.infrastructure.messaging.activity import (
    MessagingMailboxActivity,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.shared.infrastructure.db.session import get_session
from app.shared.presentation.dependencies import require_workspace
from app.shared.util.clock import now

router = APIRouter()


class MailboxResponse(BaseModel):
    id: UUID
    email_address: str
    daily_send_cap: int = Field(description="Emails this mailbox may send per UTC day")
    sent_today: int = Field(description="Emails sent since 00:00 UTC today")
    remaining_today: int
    suppressed_addresses: int = Field(
        description="Addresses in this workspace that are never mailed again"
    )


def list_mailboxes_handler(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ListMailboxesHandler:
    return ListMailboxesHandler(
        MailboxRepository(session), MessagingMailboxActivity(session)
    )


@router.get(
    "/mailboxes",
    response_model=list[MailboxResponse],
    operation_id="list_mailboxes",
    tags=["mcp"],
    summary="List the workspace's connected mailboxes with today's sending volume",
)
async def list_mailboxes(
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    handler: Annotated[ListMailboxesHandler, Depends(list_mailboxes_handler)],
) -> list[MailboxResponse]:
    return [
        MailboxResponse(
            id=overview.mailbox.id,
            email_address=overview.mailbox.email_address,
            daily_send_cap=overview.mailbox.daily_send_cap,
            sent_today=overview.sent_today,
            remaining_today=overview.remaining_today,
            suppressed_addresses=overview.suppressed_addresses,
        )
        for overview in await handler.execute(workspace_id, now())
    ]

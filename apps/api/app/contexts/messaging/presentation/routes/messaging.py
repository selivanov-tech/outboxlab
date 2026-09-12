from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.commands.send_test_email import (
    MailboxNotConfiguredError,
    SendTestEmailCommand,
    SendTestEmailHandler,
)
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)
from app.contexts.messaging.infrastructure.gmail.sender import GmailApiSender
from app.contexts.messaging.infrastructure.mailbox.gateway import MailboxGateway
from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)
from app.shared.infrastructure.db.session import get_session
from app.shared.presentation.dependencies import require_workspace

router = APIRouter()


class SendTestEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str


async def send_test_email_handler(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[SendTestEmailHandler]:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        token_provider = GoogleAccessTokenProvider(
            client,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            refresh_token=settings.google_refresh_token,
        )
        sender = GmailApiSender(client, token_provider)
        yield SendTestEmailHandler(
            MailboxGateway(MailboxRepository(session)),
            OutboundMessageRepository(session),
            sender,
        )


@router.post("/send-test-email", response_model=OutboundMessage)
async def send_test_email(
    request: SendTestEmailRequest,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    handler: Annotated[SendTestEmailHandler, Depends(send_test_email_handler)],
) -> OutboundMessage:
    command = SendTestEmailCommand(
        to_email=request.to_email,
        subject=request.subject,
        body=request.body,
    )
    try:
        return await handler.execute(command, workspace_id)
    except MailboxNotConfiguredError:
        raise HTTPException(status_code=409, detail="No mailbox configured")

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.application.queries.list_mailboxes import (
    ListMailboxesHandler,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.messaging.activity import (
    MessagingMailboxActivity,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.domain.suppression import Suppression, SuppressionReason
from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)
from app.contexts.messaging.infrastructure.persistence.suppression_repo import (
    SuppressionRepository,
)
from app.shared.util.clock import now, start_of_utc_day


async def _sent(
    session: AsyncSession, mailbox: Mailbox, number: int, *, yesterday: bool = False
) -> None:
    repo = OutboundMessageRepository(session)
    message = OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email=f"lead{number}@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id=f"<m{number}@example.com>",
    )
    if yesterday:
        message = message.model_copy(
            update={"created_at": start_of_utc_day(now()) - timedelta(hours=1)}
        )
    await repo.add(message)
    await repo.mark_sent(message.sent(f"gmail-{number}", f"thread-{number}"))


async def test_mailboxes_show_todays_volume_and_suppressions(
    session: AsyncSession,
) -> None:
    workspace = Workspace.new("acme")
    await WorkspaceRepository(session).add(workspace)
    mailbox = Mailbox.new(workspace.id, "ops@example.com", daily_send_cap=5)
    await MailboxRepository(session).add(mailbox)
    for number in (1, 2):
        await _sent(session, mailbox, number)
    await _sent(session, mailbox, 3, yesterday=True)
    suppressions = SuppressionRepository(session)
    for email, reason in (
        ("gone@example.com", SuppressionReason.HARD_BOUNCE),
        ("gone@example.com", SuppressionReason.UNSUBSCRIBE),
        ("stop@example.com", SuppressionReason.UNSUBSCRIBE),
    ):
        await suppressions.add(
            Suppression.new(
                workspace_id=workspace.id,
                email=email,
                reason=reason,
                source_inbound_id=None,
            )
        )

    (overview,) = await ListMailboxesHandler(
        MailboxRepository(session), MessagingMailboxActivity(session)
    ).execute(workspace.id, now())

    assert overview.mailbox.id == mailbox.id
    assert (overview.sent_today, overview.remaining_today) == (2, 3)
    assert overview.suppressed_addresses == 2

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.contexts.mailbox.application.ports.mailbox_activity import (
    MailboxActivityPort,
)
from app.contexts.mailbox.application.ports.mailbox_repository import (
    MailboxRepositoryPort,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.shared.util.clock import start_of_utc_day


@dataclass(frozen=True)
class MailboxOverview:
    mailbox: Mailbox
    sent_today: int
    suppressed_addresses: int

    @property
    def remaining_today(self) -> int:
        return max(self.mailbox.daily_send_cap - self.sent_today, 0)


class ListMailboxesHandler:
    def __init__(
        self, mailboxes: MailboxRepositoryPort, activity: MailboxActivityPort
    ) -> None:
        self._mailboxes = mailboxes
        self._activity = activity

    async def execute(
        self, workspace_id: UUID, moment: datetime
    ) -> list[MailboxOverview]:
        day_start = start_of_utc_day(moment)
        suppressed = await self._activity.suppressed_addresses(workspace_id)
        return [
            MailboxOverview(
                mailbox=mailbox,
                sent_today=await self._activity.sent_since(mailbox.id, day_start),
                suppressed_addresses=suppressed,
            )
            for mailbox in await self._mailboxes.list_by_workspace(workspace_id)
        ]

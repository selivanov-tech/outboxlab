import asyncio

from app.config import get_settings, resolve_workspace_id
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.shared.infrastructure.db.engine import dispose_engine
from app.shared.infrastructure.db.session import session_for_workspace


async def seed_default_mailbox() -> None:
    email = get_settings().gmail_user_email
    if not email:
        print("Skipping mailbox seed: GMAIL_USER_EMAIL not set")
        return

    workspace_id = resolve_workspace_id()
    async with session_for_workspace(workspace_id) as session:
        repo = MailboxRepository(session)
        if await repo.get_by_workspace(workspace_id) is not None:
            print(f"Mailbox already present for workspace {workspace_id}")
            return
        await repo.add(Mailbox.new(workspace_id, email))
        print(f"Seeded mailbox: {email.lower()} (workspace {workspace_id})")


async def _main() -> None:
    try:
        await seed_default_mailbox()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())

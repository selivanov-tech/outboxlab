import asyncio

from app.config import resolve_workspace_id
from app.contexts.identity.infrastructure.seed import (
    DEFAULT_WORKSPACE_NAME,
    seed_default_workspace,
)
from app.contexts.mailbox.infrastructure.seed import seed_default_mailbox
from app.shared.infrastructure.db.engine import dispose_engine


async def _main() -> None:
    try:
        await seed_default_workspace()
        print(f"Seeded workspace: {DEFAULT_WORKSPACE_NAME} ({resolve_workspace_id()})")
        await seed_default_mailbox()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())

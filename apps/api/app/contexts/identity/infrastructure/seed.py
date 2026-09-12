import asyncio

from app.config import resolve_workspace_id
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.shared.infrastructure.db.engine import dispose_engine, get_session_factory
from app.shared.util.clock import now

DEFAULT_WORKSPACE_NAME = "default"


async def seed_default_workspace() -> None:
    workspace_id = resolve_workspace_id()
    factory = get_session_factory()
    async with factory() as session:
        repo = WorkspaceRepository(session)
        if await repo.get(workspace_id) is None:
            await repo.add(
                Workspace(
                    id=workspace_id,
                    name=DEFAULT_WORKSPACE_NAME,
                    created_at=now(),
                )
            )
            await session.commit()


async def _main() -> None:
    workspace_id = resolve_workspace_id()
    try:
        await seed_default_workspace()
        print(f"Seeded workspace: {DEFAULT_WORKSPACE_NAME} ({workspace_id})")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())

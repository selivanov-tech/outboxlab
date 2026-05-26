import asyncio
import uuid

from app.identity.domain.workspace import Workspace
from app.identity.infrastructure.persistence.workspace_repo import WorkspaceRepository
from app.shared.infrastructure.db.engine import dispose_engine, get_session_factory
from app.shared.util.clock import now

DEFAULT_WORKSPACE_NAME = "default"
DEFAULT_WORKSPACE_ID = uuid.UUID("019e5f2a-1a6d-7fa2-8bee-55d3e1ccdc3d")


async def seed_default_workspace() -> None:
    factory = get_session_factory()
    async with factory() as session:
        repo = WorkspaceRepository(session)
        if await repo.get(DEFAULT_WORKSPACE_ID) is None:
            await repo.add(
                Workspace(
                    id=DEFAULT_WORKSPACE_ID,
                    name=DEFAULT_WORKSPACE_NAME,
                    created_at=now(),
                )
            )
            await session.commit()


async def _main() -> None:
    try:
        await seed_default_workspace()
        print(f"Seeded workspace: {DEFAULT_WORKSPACE_NAME} ({DEFAULT_WORKSPACE_ID})")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())

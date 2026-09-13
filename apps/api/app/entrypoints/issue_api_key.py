import asyncio

from app.config import resolve_workspace_id
from app.contexts.identity.application.commands.issue_api_key import (
    IssueApiKeyHandler,
)
from app.contexts.identity.infrastructure.persistence.api_key_repo import (
    ApiKeyRepository,
)
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.shared.infrastructure.db.engine import dispose_engine, get_session_factory


async def _main() -> None:
    workspace_id = resolve_workspace_id()
    try:
        async with get_session_factory()() as session, session.begin():
            token = await IssueApiKeyHandler(
                WorkspaceRepository(session), ApiKeyRepository(session)
            ).execute(workspace_id)
    finally:
        await dispose_engine()
    print(f"New API key for workspace {workspace_id}. It is shown only once:")
    print(token.plaintext)


if __name__ == "__main__":
    asyncio.run(_main())

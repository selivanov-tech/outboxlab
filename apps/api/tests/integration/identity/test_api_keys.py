import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.application.commands.issue_api_key import (
    IssueApiKeyHandler,
)
from app.contexts.identity.application.queries.get_my_workspace import (
    WorkspaceNotFoundError,
)
from app.contexts.identity.application.queries.resolve_api_key import (
    ResolveApiKeyHandler,
)
from app.contexts.identity.domain.api_key import ApiKey, ApiKeyToken
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.api_key_repo import (
    ApiKeyRepository,
)
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.shared.util.clock import now


async def _workspace(session: AsyncSession) -> Workspace:
    workspace = Workspace.new("acme")
    await WorkspaceRepository(session).add(workspace)
    return workspace


def _issue(session: AsyncSession) -> IssueApiKeyHandler:
    return IssueApiKeyHandler(WorkspaceRepository(session), ApiKeyRepository(session))


async def test_repository_round_trip_by_prefix(session: AsyncSession) -> None:
    workspace = await _workspace(session)
    key, _ = ApiKey.issue(workspace.id)
    repo = ApiKeyRepository(session)

    await repo.add(key)

    assert await repo.get_by_prefix(key.prefix) == key
    assert await repo.get_by_prefix("000000000000") is None


async def test_an_issued_key_resolves_to_its_workspace(session: AsyncSession) -> None:
    workspace = await _workspace(session)
    token = await _issue(session).execute(workspace.id)
    resolve = ResolveApiKeyHandler(ApiKeyRepository(session))

    assert await resolve.execute(token.plaintext) == workspace.id
    assert await resolve.execute(f"olab_{token.prefix}_wrong") is None
    assert await resolve.execute("not-a-key") is None


async def test_a_revoked_key_does_not_resolve(session: AsyncSession) -> None:
    workspace = await _workspace(session)
    key, token = ApiKey.issue(workspace.id)
    await ApiKeyRepository(session).add(key.model_copy(update={"revoked_at": now()}))

    resolved = await ResolveApiKeyHandler(ApiKeyRepository(session)).execute(
        ApiKeyToken(prefix=token.prefix, secret=token.secret).plaintext
    )

    assert resolved is None


async def test_issuing_for_an_unknown_workspace_is_rejected(
    session: AsyncSession,
) -> None:
    with pytest.raises(WorkspaceNotFoundError):
        await _issue(session).execute(uuid.uuid7())

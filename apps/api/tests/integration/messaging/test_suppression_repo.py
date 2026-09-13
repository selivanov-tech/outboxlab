from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.messaging.domain.suppression import Suppression, SuppressionReason
from app.contexts.messaging.infrastructure.persistence.suppression_repo import (
    SuppressionRepository,
)


async def _workspace(session: AsyncSession, name: str) -> Workspace:
    workspace = Workspace.new(name)
    await WorkspaceRepository(session).add(workspace)
    return workspace


async def test_suppressed_address_is_found_case_insensitively(
    session: AsyncSession,
) -> None:
    workspace = await _workspace(session, "acme")
    repo = SuppressionRepository(session)

    await repo.add(
        Suppression.new(
            workspace_id=workspace.id,
            email="Lead@Example.com",
            reason=SuppressionReason.UNSUBSCRIBE,
            source_inbound_id=None,
        )
    )

    assert await repo.is_suppressed(workspace.id, "LEAD@example.com ")
    assert not await repo.is_suppressed(workspace.id, "other@example.com")


async def test_adding_the_same_suppression_twice_is_a_no_op(
    session: AsyncSession,
) -> None:
    workspace = await _workspace(session, "acme")
    repo = SuppressionRepository(session)

    for _ in range(2):
        await repo.add(
            Suppression.new(
                workspace_id=workspace.id,
                email="lead@example.com",
                reason=SuppressionReason.HARD_BOUNCE,
                source_inbound_id=None,
            )
        )

    assert await repo.is_suppressed(workspace.id, "lead@example.com")


async def test_suppression_is_scoped_to_its_workspace(session: AsyncSession) -> None:
    owner = await _workspace(session, "owner")
    other = await _workspace(session, "other")
    await SuppressionRepository(session).add(
        Suppression.new(
            workspace_id=owner.id,
            email="lead@example.com",
            reason=SuppressionReason.UNSUBSCRIBE,
            source_inbound_id=None,
        )
    )

    assert not await SuppressionRepository(session).is_suppressed(
        other.id, "lead@example.com"
    )

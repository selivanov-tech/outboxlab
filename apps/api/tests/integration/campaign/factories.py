from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.domain.campaign import Campaign, StepDraft
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)

MAILBOX_EMAIL = "ops@example.com"
STEP_TWO_DELAY_SECONDS = 120


@dataclass(frozen=True)
class Tenant:
    workspace_id: UUID
    mailbox_id: UUID


async def seed_tenant(session: AsyncSession, name: str = "acme") -> Tenant:
    workspace = Workspace.new(name)
    await WorkspaceRepository(session).add(workspace)
    mailbox = Mailbox.new(workspace.id, MAILBOX_EMAIL)
    await MailboxRepository(session).add(mailbox)
    return Tenant(workspace_id=workspace.id, mailbox_id=mailbox.id)


def two_step_campaign(tenant: Tenant, name: str = "Q3 outreach") -> Campaign:
    return Campaign.new(
        workspace_id=tenant.workspace_id,
        mailbox_id=tenant.mailbox_id,
        name=name,
        steps=[
            StepDraft(subject="Hello", body="First touch", delay_seconds=0),
            StepDraft(
                subject="Re: Hello",
                body="Follow-up",
                delay_seconds=STEP_TWO_DELAY_SECONDS,
            ),
        ],
    )

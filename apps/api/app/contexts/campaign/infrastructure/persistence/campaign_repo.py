from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.domain.campaign import Campaign, CampaignStatus, Step
from app.contexts.campaign.infrastructure.db.models import Campaign as CampaignRow
from app.contexts.campaign.infrastructure.db.models import Step as StepRow


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, campaign: Campaign) -> None:
        self._session.add(
            CampaignRow(
                id=campaign.id,
                workspace_id=campaign.workspace_id,
                mailbox_id=campaign.mailbox_id,
                name=campaign.name,
                status=campaign.status.value,
                created_at=campaign.created_at,
            )
        )
        await self._session.flush()
        self._session.add_all(
            StepRow(
                id=step.id,
                workspace_id=campaign.workspace_id,
                campaign_id=campaign.id,
                position=step.position,
                subject=step.subject,
                body=step.body,
                delay_seconds=step.delay_seconds,
                created_at=campaign.created_at,
            )
            for step in campaign.steps
        )
        await self._session.flush()

    async def get(self, campaign_id: UUID) -> Campaign | None:
        row = await self._session.get(CampaignRow, campaign_id)
        if row is None:
            return None
        steps = await self._steps_by_campaign([campaign_id])
        return _to_domain(row, steps.get(campaign_id, []))

    async def list(self) -> list[Campaign]:
        stmt = select(CampaignRow).order_by(
            CampaignRow.created_at.desc(), CampaignRow.id.desc()
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        steps = await self._steps_by_campaign([row.id for row in rows])
        return [_to_domain(row, steps.get(row.id, [])) for row in rows]

    async def update_status(self, campaign: Campaign) -> None:
        row = await self._session.get(CampaignRow, campaign.id)
        if row is None:
            raise ValueError(f"campaign {campaign.id} not found")
        row.status = campaign.status.value
        await self._session.flush()

    async def _steps_by_campaign(
        self, campaign_ids: Sequence[UUID]
    ) -> dict[UUID, list[Step]]:
        if not campaign_ids:
            return {}
        stmt = (
            select(StepRow)
            .where(StepRow.campaign_id.in_(campaign_ids))
            .order_by(StepRow.campaign_id, StepRow.position)
        )
        grouped: dict[UUID, list[Step]] = {}
        for row in (await self._session.execute(stmt)).scalars():
            grouped.setdefault(row.campaign_id, []).append(
                Step(
                    id=row.id,
                    position=row.position,
                    subject=row.subject,
                    body=row.body,
                    delay_seconds=row.delay_seconds,
                )
            )
        return grouped


def _to_domain(row: CampaignRow, steps: Sequence[Step]) -> Campaign:
    return Campaign(
        id=row.id,
        workspace_id=row.workspace_id,
        mailbox_id=row.mailbox_id,
        name=row.name,
        status=CampaignStatus(row.status),
        steps=tuple(steps),
        created_at=row.created_at,
    )

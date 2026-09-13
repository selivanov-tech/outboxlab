from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.domain.lead import Lead, LeadState, StopReason
from app.contexts.campaign.infrastructure.db.models import Lead as LeadRow


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, leads: Sequence[Lead]) -> None:
        self._session.add_all(_to_row(lead) for lead in leads)
        await self._session.flush()

    async def get(self, lead_id: UUID) -> Lead | None:
        row = await self._session.get(LeadRow, lead_id)
        return _to_domain(row) if row is not None else None

    async def list_by_campaign(self, campaign_id: UUID) -> list[Lead]:
        stmt = (
            select(LeadRow)
            .where(LeadRow.campaign_id == campaign_id)
            .order_by(LeadRow.created_at, LeadRow.id)
        )
        return [
            _to_domain(row) for row in (await self._session.execute(stmt)).scalars()
        ]

    async def list_pending(self, campaign_id: UUID) -> list[Lead]:
        stmt = (
            select(LeadRow)
            .where(
                LeadRow.campaign_id == campaign_id,
                LeadRow.state == LeadState.PENDING.value,
            )
            .order_by(LeadRow.created_at, LeadRow.id)
        )
        return [
            _to_domain(row) for row in (await self._session.execute(stmt)).scalars()
        ]

    async def emails(self, campaign_id: UUID) -> set[str]:
        stmt = select(LeadRow.email).where(LeadRow.campaign_id == campaign_id)
        return set((await self._session.execute(stmt)).scalars())

    async def update_many(self, leads: Sequence[Lead]) -> None:
        for lead in leads:
            row = await self._session.get(LeadRow, lead.id)
            if row is None:
                raise ValueError(f"lead {lead.id} not found")
            row.state = lead.state.value
            row.steps_sent = lead.steps_sent
            row.stop_reason = (
                lead.stop_reason.value if lead.stop_reason is not None else None
            )
            row.reply_intent = lead.reply_intent
            row.updated_at = lead.updated_at
        await self._session.flush()

    async def count_by_state(
        self, campaign_ids: Sequence[UUID]
    ) -> dict[UUID, dict[LeadState, int]]:
        if not campaign_ids:
            return {}
        stmt = (
            select(LeadRow.campaign_id, LeadRow.state, func.count())
            .where(LeadRow.campaign_id.in_(campaign_ids))
            .group_by(LeadRow.campaign_id, LeadRow.state)
        )
        counts: dict[UUID, dict[LeadState, int]] = {}
        for campaign_id, state, count in (await self._session.execute(stmt)).all():
            counts.setdefault(campaign_id, {})[LeadState(state)] = int(count)
        return counts


def _to_row(lead: Lead) -> LeadRow:
    return LeadRow(
        id=lead.id,
        workspace_id=lead.workspace_id,
        campaign_id=lead.campaign_id,
        email=lead.email,
        state=lead.state.value,
        steps_sent=lead.steps_sent,
        stop_reason=lead.stop_reason.value if lead.stop_reason is not None else None,
        reply_intent=lead.reply_intent,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def _to_domain(row: LeadRow) -> Lead:
    return Lead(
        id=row.id,
        workspace_id=row.workspace_id,
        campaign_id=row.campaign_id,
        email=row.email,
        state=LeadState(row.state),
        steps_sent=row.steps_sent,
        stop_reason=StopReason(row.stop_reason)
        if row.stop_reason is not None
        else None,
        reply_intent=row.reply_intent,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.contexts.campaign.domain.send_job import (
    CLAIM_LEASE,
    SendJob,
    SendJobPayload,
    SendJobStatus,
)
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.contexts.identity.infrastructure.db.models import Workspace as WorkspaceRow
from app.shared.util.clock import now
from tests.integration.campaign.factories import Tenant, seed_tenant
from tests.integration.campaign.scenarios import start_campaign


async def _job_rows(session: AsyncSession, tenant: Tenant) -> list[SendJobRow]:
    stmt = (
        select(SendJobRow)
        .where(SendJobRow.workspace_id == tenant.workspace_id)
        .order_by(SendJobRow.scheduled_at)
        .execution_options(populate_existing=True)
    )
    return list((await session.execute(stmt)).scalars())


async def test_claim_takes_only_due_pending_jobs(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    moment = now()
    campaign, (lead,) = await start_campaign(session, tenant, ["a@example.com"])
    later = SendJob.new(
        workspace_id=tenant.workspace_id,
        mailbox_id=tenant.mailbox_id,
        payload=SendJobPayload(
            campaign_id=campaign.id,
            lead_id=lead.id,
            step_id=campaign.steps[1].id,
            step_position=2,
            to_email=lead.email,
            subject="later",
            body="later",
        ),
        scheduled_at=moment + timedelta(hours=1),
    )
    repo = SendJobRepository(session)
    await repo.add_many([later])

    claimed = await repo.claim(
        workspace_id=tenant.workspace_id,
        worker_id="worker-1",
        limit=10,
        moment=moment + timedelta(seconds=1),
        lease=CLAIM_LEASE,
    )

    assert [job.payload.step_position for job in claimed] == [1]
    assert claimed[0].attempts == 1
    assert claimed[0].payload.to_email == "a@example.com"
    due, future = await _job_rows(session, tenant)
    assert (due.status, due.locked_by) == (SendJobStatus.RUNNING.value, "worker-1")
    assert future.status == SendJobStatus.PENDING.value


async def test_claim_ignores_other_workspaces(session: AsyncSession) -> None:
    tenant_a = await seed_tenant(session, "tenant-a")
    tenant_b = await seed_tenant(session, "tenant-b")
    await start_campaign(session, tenant_a, ["a@example.com"])
    await start_campaign(session, tenant_b, ["b@example.com"])

    claimed = await SendJobRepository(session).claim(
        workspace_id=tenant_a.workspace_id,
        worker_id="worker-1",
        limit=10,
        moment=now() + timedelta(seconds=1),
        lease=CLAIM_LEASE,
    )

    assert [job.payload.to_email for job in claimed] == ["a@example.com"]


async def test_running_job_is_reclaimed_only_after_the_lease(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    await start_campaign(session, tenant, ["a@example.com"])
    repo = SendJobRepository(session)
    first_claim = now() + timedelta(seconds=1)

    async def claim_at(offset: timedelta, worker_id: str) -> list[int]:
        jobs = await repo.claim(
            workspace_id=tenant.workspace_id,
            worker_id=worker_id,
            limit=10,
            moment=first_claim + offset,
            lease=CLAIM_LEASE,
        )
        return [job.attempts for job in jobs]

    assert await claim_at(timedelta(0), "worker-1") == [1]
    assert await claim_at(timedelta(minutes=1), "worker-2") == []
    assert await claim_at(CLAIM_LEASE + timedelta(seconds=1), "worker-2") == [2]
    (row,) = await _job_rows(session, tenant)
    assert row.locked_by == "worker-2"


async def test_release_reschedules_without_counting_the_attempt(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    await start_campaign(session, tenant, ["a@example.com"])
    repo = SendJobRepository(session)
    moment = now() + timedelta(seconds=1)
    (job,) = await repo.claim(
        workspace_id=tenant.workspace_id,
        worker_id="worker-1",
        limit=10,
        moment=moment,
        lease=CLAIM_LEASE,
    )
    retry_at = moment + timedelta(hours=3)

    await repo.release(job.id, retry_at, "daily cap reached", moment)

    (row,) = await _job_rows(session, tenant)
    assert row.status == SendJobStatus.PENDING.value
    assert row.attempts == 0
    assert row.scheduled_at == retry_at
    assert row.locked_by is None
    assert row.last_error == "daily cap reached"


async def test_concurrent_claims_never_return_the_same_job(
    engine: AsyncEngine,
) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as setup, setup.begin():
        tenant = await seed_tenant(setup, "skip-locked")
        await start_campaign(setup, tenant, ["a@example.com", "b@example.com"])
    moment = now() + timedelta(seconds=1)

    try:
        async with engine.connect() as conn_a, engine.connect() as conn_b:
            await conn_a.begin()
            await conn_b.begin()
            claim_a = await SendJobRepository(AsyncSession(bind=conn_a)).claim(
                workspace_id=tenant.workspace_id,
                worker_id="worker-a",
                limit=1,
                moment=moment,
                lease=CLAIM_LEASE,
            )
            claim_b = await SendJobRepository(AsyncSession(bind=conn_b)).claim(
                workspace_id=tenant.workspace_id,
                worker_id="worker-b",
                limit=10,
                moment=moment,
                lease=CLAIM_LEASE,
            )
            await conn_a.rollback()
            await conn_b.rollback()
    finally:
        async with AsyncSession(engine) as cleanup, cleanup.begin():
            await cleanup.execute(
                delete(WorkspaceRow).where(WorkspaceRow.id == tenant.workspace_id)
            )

    ids_a = {job.id for job in claim_a}
    ids_b = {job.id for job in claim_b}
    assert len(ids_a) == 1
    assert len(ids_b) == 1
    assert ids_a.isdisjoint(ids_b)

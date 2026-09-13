import hmac
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.contexts.campaign.application.process_send_jobs import (
    ProcessClaimedSendJobHandler,
    ProcessSendJobByIdHandler,
    SendJobNotClaimedError,
)
from app.contexts.campaign.infrastructure.metrics import record_send_job_outcome
from app.contexts.campaign.infrastructure.messaging.email_dispatch import (
    gmail_email_dispatch,
)
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.shared.infrastructure.db.session import get_session
from app.shared.presentation.dependencies import require_workspace
from app.shared.util.clock import now

router = APIRouter(prefix="/internal", include_in_schema=False)


class ProcessSendJobResponse(BaseModel):
    job_id: UUID
    outcome: str


async def require_internal_token(
    settings: Annotated[Settings, Depends(get_settings)],
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.internal_api_token
    if (
        not expected
        or x_internal_token is None
        or not hmac.compare_digest(x_internal_token, expected)
    ):
        raise HTTPException(status_code=401, detail="Invalid internal token")


async def process_send_job_by_id_handler(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[ProcessSendJobByIdHandler]:
    async with httpx.AsyncClient() as client:
        jobs = SendJobRepository(session)
        yield ProcessSendJobByIdHandler(
            jobs,
            ProcessClaimedSendJobHandler(
                CampaignRepository(session),
                LeadRepository(session),
                jobs,
                gmail_email_dispatch(session, client, settings),
            ),
        )


@router.post(
    "/send-jobs/{job_id}/process",
    response_model=ProcessSendJobResponse,
    dependencies=[Depends(require_internal_token)],
)
async def process_send_job(
    job_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    handler: Annotated[
        ProcessSendJobByIdHandler, Depends(process_send_job_by_id_handler)
    ],
) -> ProcessSendJobResponse:
    try:
        processed = await handler.execute(
            job_id=job_id, workspace_id=workspace_id, moment=now()
        )
    except SendJobNotClaimedError:
        raise HTTPException(status_code=409, detail="Send job is not claimed")
    record_send_job_outcome(processed.job, processed.outcome, now())
    return ProcessSendJobResponse(job_id=job_id, outcome=processed.outcome.value)

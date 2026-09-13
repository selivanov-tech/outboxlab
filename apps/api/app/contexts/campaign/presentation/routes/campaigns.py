from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.commands.add_leads import AddLeadsHandler
from app.contexts.campaign.application.commands.create_campaign import (
    CreateCampaignCommand,
    CreateCampaignHandler,
)
from app.contexts.campaign.application.commands.start_campaign import (
    StartCampaignHandler,
)
from app.contexts.campaign.application.errors import (
    CampaignHasNoLeadsError,
    CampaignNotFoundError,
    MailboxNotConnectedError,
)
from app.contexts.campaign.application.queries.get_campaign import GetCampaignHandler
from app.contexts.campaign.application.queries.get_campaign_metrics import (
    GetCampaignMetricsHandler,
)
from app.contexts.campaign.application.queries.list_campaigns import (
    ListCampaignsHandler,
)
from app.contexts.campaign.domain.campaign import Campaign, Step, StepDraft
from app.contexts.campaign.domain.errors import (
    CampaignHasNoStepsError,
    NegativeStepDelayError,
)
from app.contexts.campaign.infrastructure.mailbox.lookup import MailboxLookup
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.shared.infrastructure.db.session import get_session
from app.shared.presentation.dependencies import require_workspace
from app.shared.util.clock import now

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
WorkspaceId = Annotated[UUID, Depends(require_workspace)]

_CAMPAIGN_NOT_FOUND = HTTPException(status_code=404, detail="Campaign not found")


class StepRequest(BaseModel):
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    delay_seconds: int = Field(ge=0)


class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    steps: list[StepRequest] = Field(min_length=1)


class AddLeadsRequest(BaseModel):
    emails: list[EmailStr] = Field(min_length=1, max_length=1000)


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    status: str
    mailbox_id: UUID
    steps: list[Step]
    created_at: datetime


class CampaignSummaryResponse(CampaignResponse):
    lead_counts: dict[str, int]


class LeadResponse(BaseModel):
    id: UUID
    email: str
    state: str
    steps_sent: int
    stop_reason: str | None
    reply_intent: str | None
    next_send_at: datetime | None
    updated_at: datetime


class CampaignDetailResponse(CampaignResponse):
    leads: list[LeadResponse]


class AddLeadsResponse(BaseModel):
    added: int
    skipped: int
    scheduled: int


class StartCampaignResponse(BaseModel):
    status: str
    scheduled: int


class CampaignMetricsResponse(BaseModel):
    campaign_id: UUID
    leads: int
    contacted: int = Field(description="Leads that received at least one step")
    emails_sent: int
    replied: int = Field(
        description="Leads whose reply was classified, bounces excluded"
    )
    reply_intents: dict[str, int]
    bounced: int
    in_progress: int = Field(description="Leads pending, scheduled or between steps")
    completed: int = Field(description="Leads that received every step")
    reply_rate: float = Field(description="replied / contacted")
    bounce_rate: float = Field(description="bounced / contacted")


def create_campaign_handler(session: Session) -> CreateCampaignHandler:
    return CreateCampaignHandler(
        MailboxLookup(MailboxRepository(session)), CampaignRepository(session)
    )


def list_campaigns_handler(session: Session) -> ListCampaignsHandler:
    return ListCampaignsHandler(CampaignRepository(session), LeadRepository(session))


def get_campaign_handler(session: Session) -> GetCampaignHandler:
    return GetCampaignHandler(
        CampaignRepository(session), LeadRepository(session), SendJobRepository(session)
    )


def add_leads_handler(session: Session) -> AddLeadsHandler:
    return AddLeadsHandler(
        CampaignRepository(session), LeadRepository(session), SendJobRepository(session)
    )


def get_campaign_metrics_handler(session: Session) -> GetCampaignMetricsHandler:
    return GetCampaignMetricsHandler(
        CampaignRepository(session), LeadRepository(session)
    )


def start_campaign_handler(session: Session) -> StartCampaignHandler:
    return StartCampaignHandler(
        CampaignRepository(session), LeadRepository(session), SendJobRepository(session)
    )


def _campaign_fields(campaign: Campaign) -> dict[str, object]:
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status.value,
        "mailbox_id": campaign.mailbox_id,
        "steps": list(campaign.steps),
        "created_at": campaign.created_at,
    }


@router.post(
    "/campaigns",
    status_code=201,
    response_model=CampaignResponse,
    operation_id="create_campaign",
    tags=["mcp"],
    summary="Create a draft campaign with ordered steps, sent from the workspace mailbox",
    responses={409: {"description": "No mailbox connected to this workspace"}},
)
async def create_campaign(
    request: CreateCampaignRequest,
    workspace_id: WorkspaceId,
    handler: Annotated[CreateCampaignHandler, Depends(create_campaign_handler)],
) -> CampaignResponse:
    command = CreateCampaignCommand(
        name=request.name,
        steps=tuple(
            StepDraft(
                subject=step.subject, body=step.body, delay_seconds=step.delay_seconds
            )
            for step in request.steps
        ),
    )
    try:
        campaign = await handler.execute(command, workspace_id)
    except MailboxNotConnectedError:
        raise HTTPException(
            status_code=409, detail="No mailbox connected to this workspace"
        )
    except CampaignHasNoStepsError, NegativeStepDelayError:
        raise HTTPException(status_code=422, detail="Invalid campaign steps")
    return CampaignResponse.model_validate(_campaign_fields(campaign))


@router.get(
    "/campaigns",
    response_model=list[CampaignSummaryResponse],
    operation_id="list_campaigns",
    tags=["mcp"],
    summary="List campaigns with lead counts by state",
)
async def list_campaigns(
    _: WorkspaceId,
    handler: Annotated[ListCampaignsHandler, Depends(list_campaigns_handler)],
) -> list[CampaignSummaryResponse]:
    return [
        CampaignSummaryResponse.model_validate(
            {
                **_campaign_fields(summary.campaign),
                "lead_counts": {
                    state.value: count for state, count in summary.lead_counts.items()
                },
            }
        )
        for summary in await handler.execute()
    ]


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignDetailResponse,
    operation_id="get_campaign",
    tags=["mcp"],
    summary="Get a campaign with its steps and every lead's state",
    responses={404: {"description": "Campaign not found"}},
)
async def get_campaign(
    campaign_id: UUID,
    _: WorkspaceId,
    handler: Annotated[GetCampaignHandler, Depends(get_campaign_handler)],
) -> CampaignDetailResponse:
    try:
        detail = await handler.execute(campaign_id)
    except CampaignNotFoundError:
        raise _CAMPAIGN_NOT_FOUND
    return CampaignDetailResponse.model_validate(
        {
            **_campaign_fields(detail.campaign),
            "leads": [
                LeadResponse(
                    id=view.lead.id,
                    email=view.lead.email,
                    state=view.lead.state.value,
                    steps_sent=view.lead.steps_sent,
                    stop_reason=(
                        view.lead.stop_reason.value
                        if view.lead.stop_reason is not None
                        else None
                    ),
                    reply_intent=view.lead.reply_intent,
                    next_send_at=view.next_send_at,
                    updated_at=view.lead.updated_at,
                )
                for view in detail.leads
            ],
        }
    )


@router.post(
    "/campaigns/{campaign_id}/leads",
    response_model=AddLeadsResponse,
    operation_id="add_leads_to_campaign",
    tags=["mcp"],
    summary="Add lead email addresses; they are scheduled at once if the campaign is active",
    responses={404: {"description": "Campaign not found"}},
)
async def add_leads(
    campaign_id: UUID,
    request: AddLeadsRequest,
    _: WorkspaceId,
    handler: Annotated[AddLeadsHandler, Depends(add_leads_handler)],
) -> AddLeadsResponse:
    try:
        result = await handler.execute(campaign_id, list(request.emails), now())
    except CampaignNotFoundError:
        raise _CAMPAIGN_NOT_FOUND
    return AddLeadsResponse(
        added=result.added, skipped=result.skipped, scheduled=result.scheduled
    )


@router.post(
    "/campaigns/{campaign_id}/start",
    response_model=StartCampaignResponse,
    operation_id="start_campaign",
    tags=["mcp"],
    summary="Start a campaign: schedule the first step for every pending lead (idempotent)",
    responses={
        404: {"description": "Campaign not found"},
        422: {"description": "The campaign has no leads to start"},
    },
)
async def start_campaign(
    campaign_id: UUID,
    _: WorkspaceId,
    handler: Annotated[StartCampaignHandler, Depends(start_campaign_handler)],
) -> StartCampaignResponse:
    try:
        result = await handler.execute(campaign_id, now())
    except CampaignNotFoundError:
        raise _CAMPAIGN_NOT_FOUND
    except CampaignHasNoLeadsError:
        raise HTTPException(
            status_code=422, detail="The campaign has no leads to start"
        )
    return StartCampaignResponse(
        status=result.campaign.status.value, scheduled=result.scheduled
    )


@router.get(
    "/campaigns/{campaign_id}/metrics",
    response_model=CampaignMetricsResponse,
    operation_id="get_campaign_metrics",
    tags=["mcp"],
    summary="Get a campaign's sending, reply and bounce numbers",
    responses={404: {"description": "Campaign not found"}},
)
async def get_campaign_metrics(
    campaign_id: UUID,
    _: WorkspaceId,
    handler: Annotated[
        GetCampaignMetricsHandler, Depends(get_campaign_metrics_handler)
    ],
) -> CampaignMetricsResponse:
    try:
        metrics = await handler.execute(campaign_id)
    except CampaignNotFoundError:
        raise _CAMPAIGN_NOT_FOUND
    return CampaignMetricsResponse.model_validate(metrics, from_attributes=True)

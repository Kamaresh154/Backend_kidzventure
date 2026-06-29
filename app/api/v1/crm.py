
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, resolve_org_id
from app.schemas.crm import ActivityCreate, ActivityResponse, LeadCreate, LeadListResponse, LeadResponse, LeadUpdate
from app.services import crm_service

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    db: DbSession,
    current: CurrentUserDep,
    status: str | None = None,
    center_id: UUID | None = None,
    assigned_to: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> LeadListResponse:
    current.require_permission("crm.read")
    org_id = await resolve_org_id(current, db)
    items, total = await crm_service.list_leads(
        db, org_id, status=status, center_id=center_id,
        assigned_to=assigned_to, page=page, page_size=page_size,
    )
    return LeadListResponse(items=[LeadResponse.model_validate(l) for l in items], total=total, page=page, page_size=page_size)


@router.post("/leads", response_model=LeadResponse, status_code=201)
async def create_lead(data: LeadCreate, db: DbSession, current: CurrentUserDep) -> LeadResponse:
    current.require_permission("crm.write")
    org_id = await resolve_org_id(current, db)
    lead = await crm_service.create_lead(db, org_id, data)
    return LeadResponse.model_validate(lead)


@router.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: UUID, data: LeadUpdate, db: DbSession, current: CurrentUserDep) -> LeadResponse:
    current.require_permission("crm.write")
    org_id = await resolve_org_id(current, db)
    lead = await crm_service.update_lead(db, org_id, lead_id, data)
    return LeadResponse.model_validate(lead)


@router.delete("/leads/{lead_id}", status_code=204)
async def delete_lead(lead_id: UUID, db: DbSession, current: CurrentUserDep) -> None:
    current.require_permission("crm.write")
    org_id = await resolve_org_id(current, db)
    await crm_service.delete_lead(db, org_id, lead_id)


@router.post("/leads/{lead_id}/activities", response_model=ActivityResponse, status_code=201)
async def add_activity(lead_id: UUID, data: ActivityCreate, db: DbSession, current: CurrentUserDep) -> ActivityResponse:
    current.require_permission("crm.write")
    org_id = await resolve_org_id(current, db)
    activity = await crm_service.add_activity(db, org_id, lead_id, data, current.user.id)
    return ActivityResponse.model_validate(activity)


@router.get("/pipeline/stats")
async def pipeline_stats(db: DbSession, current: CurrentUserDep) -> dict:
    current.require_permission("crm.read")
    org_id = await resolve_org_id(current, db)
    return await crm_service.get_pipeline_stats(db, org_id)
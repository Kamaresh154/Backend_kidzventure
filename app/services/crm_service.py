import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm import Lead, LeadActivity
from app.schemas.crm import ActivityCreate, LeadCreate, LeadUpdate

VALID_STATUSES = {"new", "contacted", "trial_scheduled", "trial_done", "enrolled", "lost"}


async def list_leads(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str | None = None,
    center_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Lead], int]:
    q = (
        select(Lead)
        .where(Lead.organization_id == org_id, Lead.deleted_at.is_(None))
        .options(selectinload(Lead.activities))
    )
    if status:
        q = q.where(Lead.status == status)
    if center_id:
        q = q.where(Lead.center_id == center_id)
    if assigned_to:
        q = q.where(Lead.assigned_to == assigned_to)
    total = (await db.execute(select(func.count()).select_from(
        select(Lead).where(Lead.organization_id == org_id, Lead.deleted_at.is_(None)).subquery()
    ))).scalar_one()
    items = (
        await db.execute(q.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return list(items), total


async def create_lead(db: AsyncSession, org_id: uuid.UUID, data: LeadCreate) -> Lead:
    lead = Lead(organization_id=org_id, **data.model_dump())
    db.add(lead)
    await db.commit()
    # Re-fetch with activities eagerly loaded to avoid MissingGreenlet error
    # when Pydantic serializes LeadResponse.activities
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead.id)
        .options(selectinload(Lead.activities))
    )
    return result.scalar_one()


async def update_lead(
    db: AsyncSession, org_id: uuid.UUID, lead_id: uuid.UUID, data: LeadUpdate
) -> Lead:
    lead = await _get_lead(db, org_id, lead_id)
    updates = data.model_dump(exclude_none=True)
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
    for k, v in updates.items():
        setattr(lead, k, v)
    await db.commit()
    # Re-fetch with activities eagerly loaded
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(selectinload(Lead.activities))
    )
    return result.scalar_one()


async def add_activity(
    db: AsyncSession,
    org_id: uuid.UUID,
    lead_id: uuid.UUID,
    data: ActivityCreate,
    created_by: uuid.UUID,
) -> LeadActivity:
    lead = await _get_lead(db, org_id, lead_id)
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type=data.activity_type,
        description=data.description,
        created_by=created_by,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


async def delete_lead(db: AsyncSession, org_id: uuid.UUID, lead_id: uuid.UUID) -> None:
    from datetime import datetime, timezone
    lead = await _get_lead(db, org_id, lead_id)
    lead.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def _get_lead(db: AsyncSession, org_id: uuid.UUID, lead_id: uuid.UUID) -> Lead:
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id, Lead.organization_id == org_id, Lead.deleted_at.is_(None))
        .options(selectinload(Lead.activities))
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


async def get_pipeline_stats(db: AsyncSession, org_id: uuid.UUID) -> dict:
    rows = (
        await db.execute(
            select(Lead.status, func.count().label("count"))
            .where(Lead.organization_id == org_id, Lead.deleted_at.is_(None))
            .group_by(Lead.status)
        )
    ).all()
    return {row.status: row.count for row in rows}
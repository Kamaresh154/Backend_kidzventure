import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Center, Organization
from app.schemas.organization import CenterCreate, CenterUpdate, OrganizationUpdate


async def get_organization(db: AsyncSession, org_id: uuid.UUID) -> Organization:
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        )
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def update_organization(
    db: AsyncSession, org_id: uuid.UUID, data: OrganizationUpdate
) -> Organization:
    org = await get_organization(db, org_id)
    if data.name is not None:
        org.name = data.name
    if data.plan is not None:
        org.plan = data.plan
    if data.settings is not None:
        org.settings = data.settings
    return org


async def list_centers(db: AsyncSession, org_id: uuid.UUID) -> list[Center]:
    result = await db.execute(
        select(Center)
        .where(Center.organization_id == org_id, Center.deleted_at.is_(None))
        .order_by(Center.name)
    )
    return list(result.scalars().all())


async def create_center(db: AsyncSession, org_id: uuid.UUID, data: CenterCreate) -> Center:
    await get_organization(db, org_id)
    if data.code:
        dup = await db.execute(
            select(Center).where(
                Center.organization_id == org_id,
                Center.code == data.code,
                Center.deleted_at.is_(None),
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Center code already exists")

    center = Center(
        organization_id=org_id,
        name=data.name,
        code=data.code,
        address=data.address,
        timezone=data.timezone,
    )
    db.add(center)
    await db.flush()
    return center


async def get_center(db: AsyncSession, org_id: uuid.UUID, center_id: uuid.UUID) -> Center:
    result = await db.execute(
        select(Center).where(
            Center.id == center_id,
            Center.organization_id == org_id,
            Center.deleted_at.is_(None),
        )
    )
    center = result.scalar_one_or_none()
    if center is None:
        raise HTTPException(status_code=404, detail="Center not found")
    return center


async def update_center(
    db: AsyncSession, org_id: uuid.UUID, center_id: uuid.UUID, data: CenterUpdate
) -> Center:
    center = await get_center(db, org_id, center_id)
    if data.name is not None:
        center.name = data.name
    if data.code is not None:
        center.code = data.code
    if data.address is not None:
        center.address = data.address
    if data.timezone is not None:
        center.timezone = data.timezone
    return center


async def soft_delete_center(db: AsyncSession, org_id: uuid.UUID, center_id: uuid.UUID) -> None:
    from datetime import datetime, timezone

    center = await get_center(db, org_id, center_id)
    center.deleted_at = datetime.now(timezone.utc)
